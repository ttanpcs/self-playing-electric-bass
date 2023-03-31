from json import load
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
import RPi.GPIO as GPIO

# DONT BE AN IDIOT TONY FIND MAC ADDRESS AND ADD TO BLUETOOTH DEVICES ON ILLINOIS GUEST DEVICES...
# See if Pluckers work
# See if other things work

NUM_FRETS = 7
NUM_IN_SCALE = 12
PWM_SLEEP = 0.5
STEP_SLEEP = 0.0003

def load_motors(file_path='motor_config.json'):
    with open(file_path, 'r') as f:
        motors = load(f)
        motor_set = MotorSet()
        for motor in motors:
            motor_set.add(Motor(motor['direction'], motor['step'], motor['bass'], motor['pwm'], motor['pwm_list']))
        
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
        future = self.executor.submit(mc.play, note)

class Motor:
    def __init__(self, direction, step, bass, pwm, pwm_list):
        self.direction = direction
        self.step = step
        self.low = bass
        self.pwm = pwm
        self.high = bass + NUM_FRETS - 1
        self.pwm_list = pwm_list
        self.pwm_index = 0
        self.location = 0

        GPIO.setup(self.direction, GPIO.OUT)
        GPIO.setup(self.step, GPIO.OUT)
        GPIO.output(self.direction, GPIO.LOW)
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

    def move(self, num_steps):
        for i in range(num_steps):
            sleep(STEP_SLEEP)
            GPIO.output(self.step, GPIO.LOW)
            sleep(STEP_SLEEP)
            GPIO.outpu(self.step, GPIO.HIGH)

    def pluck(self):
        self.pwm_index = (self.pwm_index + 1) % len(self.pwm_list)
        self.pwm_control.ChangeDutyCycle(self.pwm_list[self.pwm_index])
        sleep(PWM_SLEEP)

    def play(self, note):
        _, adjusted_note = self.getAdjustedNote(note)
        self.a_lock.acquire()
        
        # change direction
        # calculate num steps
        # move
        self.pluck()

        self.l_lock.acquire()
        self.location = adjusted_note - self.low
        self.l_lock.release()

        self.a_lock.release()
