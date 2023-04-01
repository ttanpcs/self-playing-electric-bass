from json import load
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
import RPi.GPIO as GPIO

NUM_FRETS = 7
NUM_IN_SCALE = 12
PWM_SLEEP = 0.5
STEP_SLEEP = 0.0009

def load_motors(file_path='motor_config.json'):
    with open(file_path, 'r') as f:
        motors = load(f)
        motor_set = MotorSet()
        for motor in motors:
            motor_set.add(Motor(motor['direction'], motor['step'], motor['bass'], motor['pwm'], motor['pwm_list'], motor['voltage'], motor['multiplier']))
        
        return motor_set

class MotorSet:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.executor = ThreadPoolExecutor()
        self.motors = []
    
    def add(self, motor):
        self.motors.append(motor)

    def play_note(self, note):
        mc = min(self.motors, key=lambda m: m.score(note))
        print(note)
        future = self.executor.submit(mc.play, note)

class Motor:
    def __init__(self, direction, step, bass, pwm, pwm_list, voltage, multiplier):
        self.direction = direction
        self.step = step
        self.low = bass
        self.pwm = pwm
        self.high = bass + NUM_FRETS - 1
        self.pwm_list = pwm_list
        self.pwm_index = 0
        self.location = 0
        self.multiplier = multiplier
        self.voltage = voltage
        self.distances = [1.625, 1.5, 1.44, 1.375, 1.25, 1.1875]

        GPIO.setup(self.direction, GPIO.OUT)
        GPIO.setup(self.step, GPIO.OUT)
        GPIO.output(self.direction, voltage)
        GPIO.output(self.step, GPIO.LOW)

        GPIO.setup(self.pwm, GPIO.OUT)
        self.pwm_control = GPIO.PWM(self.pwm, 50)
        self.pwm_control.start(self.pwm_list[0])
        sleep(PWM_SLEEP)

        self.a_lock = Lock()
        self.l_lock = Lock()
    
    def __del__(self):
        self.pwm_control.stop()

    def score(self, note):
        score = 0
        adjusted, adjusted_note = self.getAdjustedNote(note)
        if self.a_lock.acquire(blocking=False):
            self.a_lock.release()
        else:
            score += NUM_FRETS
        if adjusted:
            score += 2 * NUM_FRETS
        self.l_lock.acquire()
        score += int(abs(adjusted_note - (self.location + self.low)))
        self.l_lock.release()
        
        return score

    def getAdjustedNote(self, note):
        if note < self.low or note > self.high:
            if note < self.low:
                return True, (int((self.low - note) / NUM_IN_SCALE) + 1) * NUM_IN_SCALE + note
            else:
                return True, note - (int((note - self.high) / NUM_IN_SCALE) + 1) * NUM_IN_SCALE
        else:
            return False, note

    def find_num_steps(self, note):
        if note - self.location - self.low > 0:
            GPIO.output(self.direction, self.voltage)
        else:
            GPIO.output(self.direction, (self.voltage + 1) % 2)
        calc = sum(self.distances[min(self.location, note - self.low): max(self.location, note - self.low)])
        return calc

    def move(self, num_steps):
        for i in range(int(num_steps)):
            sleep(STEP_SLEEP)
            GPIO.output(self.step, GPIO.LOW)
            sleep(STEP_SLEEP)
            GPIO.output(self.step, GPIO.HIGH)

    def pluck(self):
        self.pwm_index = (self.pwm_index + 1) % len(self.pwm_list)
        self.pwm_control.ChangeDutyCycle(self.pwm_list[self.pwm_index])
        sleep(PWM_SLEEP)

    def play(self, note):
        _, adjusted_note = self.getAdjustedNote(note)
        self.a_lock.acquire()
        self.l_lock.acquire()
        calc = self.find_num_steps(note)
        self.l_lock.release()
        self.move(calc / self.multiplier)
        sleep(0.1)
        self.pluck()

        self.l_lock.acquire()
        self.location = adjusted_note - self.low
        self.l_lock.release()

        self.a_lock.release()
