import RPi.GPIO as GPIO
import time

class ServoController:
    def __init__(self, pin, freq=50, width_min=2.5, width_max=12.5, tap_interval=1.0):
        self.servo_pin = pin
        self.servo_freq = freq
        self.servo_width_min = width_min
        self.servo_width_max = width_max
        self.total_taps = 0
        self.current_taps = 0
        self.keep_tapping = False
        self.wait_for_tap = 0
        self.last_tap_time = 0
        self.tap_interval = tap_interval

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.servo = GPIO.PWM(self.servo_pin, self.servo_freq)
        self.servo.start(0)

    def servo_map(self, value, range_min, range_max):
        percent = (value - range_min) / (range_max - range_min)
        return self.servo_width_min + percent * (self.servo_width_max - self.servo_width_min)

    def move_servo(self, angle):
        duty_cycle = self.servo_map(angle, 0, 180)
        self.servo.ChangeDutyCycle(duty_cycle)

    def tap_once(self):
        if time.time() - self.last_tap_time >= self.tap_interval:
            for angle in range(116, 71, -4):
                self.move_servo(angle)
                time.sleep(0.02)

            time.sleep(0.3)

            for angle in range(72, 117, 4):
                self.move_servo(angle)
                time.sleep(0.02)

            self.total_taps += 1
            self.current_taps += 1
            self.last_tap_time = time.time()

    def toggle_auto(self):
        if self.keep_tapping:
            self.keep_tapping = False
        else:
            self.keep_tapping = True

    def add_tap_time(self, n):
        if isinstance(n, int) and n > 0:
            self.wait_for_tap += n

    def reset_current_taps(self):
        self.current_taps = 0

    def cleanup(self):
        self.servo.stop()


def main():
    servo_controller = ServoController(pin=12)
    servo_controller.keep_tapping = True  # 开启自动敲击

    try:
        while True:
            if servo_controller.keep_tapping:
                servo_controller.tap_once()
                print(f"Total taps: {servo_controller.total_taps}, Current taps: {servo_controller.current_taps}")
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        servo_controller.cleanup()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
