from motor_control import load_motors
from time import sleep

motor_set = load_motors()

# motor_set.play_note(52)
# motor_set.play_note(42)
# motor_set.play_note(52)

# If pwm doesn't work we will just make the lock a global lock and stall for everything...
# Plucking test
for motor in motor_set.motors:
    print(motor.pwm)
    motor.pluck()
    sleep(2)