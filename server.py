from bluedot.btcomm import BlueToothServer
from motor_control import load_motors
from signal import pause

motors = load_motors()

def on_note(data):
    motors.play_note(int(data.split()[0]))

s = BlueToothServer(on_note, power_up_device=True)
pause()