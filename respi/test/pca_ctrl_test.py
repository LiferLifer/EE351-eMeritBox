import time
from Adafruit_PCA9685 import PCA9685

pwm = PCA9685()

pwm.set_pwm_freq(50)

servo_channel = 7

servo_min = 500
servo_max = 2500

def set_servo_angle(channel, angle):
    pulse_width = int((angle / 180.0) * (servo_max - servo_min) + servo_min)
    pwm.set_pwm(channel, 0, 1500)


try:
    while True:
        set_servo_angle(servo_channel, 135)
        print(1)
        time.sleep(1)

        set_servo_angle(servo_channel, 75)
        time.sleep(1)

except KeyboardInterrupt:
    pwm.set_all_pwm(0, 0)
