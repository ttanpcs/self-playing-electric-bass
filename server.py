from bluedot.btcomm import BluetoothServer
from motor_control import load_motors
from signal import pause

motors = load_motors()

def on_note(data):
    if data == "stop":
        print("stopping")
        for motor in motors.motors:
            calc = motor.find_num_steps(motor.low)
            motor.move(calc / motor.multiplier)
            if motor.pwm_index == 1:
                motor.pluck()
    else:
        motors.play_note(int(data.split()[0]))

s = BluetoothServer(on_note, power_up_device=True)
pause()