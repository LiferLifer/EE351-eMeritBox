import time, serial, random, vlc, os
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from PIL import Image, ImageFont
import _thread
import flask
# from flask_cors import CORS
from port import port

try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error importing RPi.GPIO! Maybe try with 'sudo' again...")

servo_PIN = 12
servo_freq = 50
servo_width_min = 2.5
servo_width_max = 12.5

button1_pin = 19  # Right_Key
button2_pin = 26  # Left_Key
button_pin = 21


class BGMPlayer:
    def __init__(self):
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()

    def load_music(self, music_path):
        media = self.instance.media_new(music_path)
        self.player.set_media(media)

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()


class OLEDCtrl:
    def __init__(self, port=0, address=0x3C):
        serial = i2c(port=port, address=address)
        self.oled = sh1106(serial)
        # self.font = ImageFont.load_default()
        font_path = "/home/gugu/eMeritBox/res/YaHei.ttf"
        font_size = 10
        self.font = ImageFont.truetype(font_path, font_size)

    def display_status(self, servo_controller = None, box = None):
        with canvas(self.oled) as draw:
            localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            draw.text((3, 5), localtime, font=self.font, fill=255)
            text = "Welcome to eMeritBox!"
            if not box == None and box.box_is_open:
                text = "Merit donation is open..."
            draw.text((3, 16), text, font=self.font, fill=255)
            if not servo_controller == None:
                cur, tot, wait, auto = servo_controller.get_disp_cont()
                cur = box.snow_num
                status = f">> Cur: {cur}  & Tot: {tot}"
                draw.text((3, 27), status, font=self.font, fill=255)
                status = f">> Auto:{auto} & D: {box.box_is_open}"
                draw.text((3, 37), status, font=self.font, fill=255)
                status = f">> Wait: {wait} tap(s)"
                draw.text((3, 47), status, font=self.font, fill=255)


class SnowBox:
    def __init__(self, row, col, direction=4):
        self.row = row
        self.col = col
        self.box_size = row * col
        self.box = [0] * self.box_size
        self.snow_num = 0
        self.g_direction = direction  # 向下
        self.box_is_open = False

    def add_snow(self, n):  # 暂时在顶部添加
        if isinstance(n, int) and n > 0:
            for _ in range(n):
                if self.g_direction == 4:
                    zero_indices = [i for i, x in enumerate(self.box[:self.col]) if x == 0]
                elif self.g_direction == 0:
                    zero_indices = [i for i, x in enumerate(self.box[-self.col:]) if x == 0]
                    zero_indices = [i + self.box_size - self.col for i in zero_indices]
                elif self.g_direction == 2:
                    zero_indices = [i for i in range(0, self.box_size, self.col) if self.box[i] == 0]
                elif self.g_direction == 6:
                    zero_indices = [i for i in range(self.col - 1, self.box_size, self.col) if self.box[i] == 0]
                elif self.g_direction == 7:
                    i = self.row - 1
                    zero_indices = [i] if self.box[i] == 0 else False
                elif self.g_direction == 5:
                    i = self.box_size - 1
                    zero_indices = [i] if self.box[i] == 0 else False
                elif self.g_direction == 1:
                    i = self.row * (self.col - 1)
                    zero_indices = [i] if self.box[i] == 0 else False
                elif self.g_direction == 3:
                    zero_indices = [0] if self.box[0] == 0 else False

                if zero_indices:
                    random_index = random.choice(zero_indices)
                    self.box[random_index] = 1
                    self.snow_num += 1

    def change_g(self, direction):
        self.g_direction = direction
        
    def get_new_position(self, idx, direction):
        if idx < 0 or idx >= self.box_size:  # 检查索引是否在范围内
            return None

        row, col = idx // self.col, idx % self.col

        if direction == 0 and row > 0:  # 上
            return idx - self.col
        elif direction == 1 and row > 0 and col < self.col - 1:  # 右上
            return idx - self.col + 1
        elif direction == 2 and col < self.col - 1:  # 右
            return idx + 1
        elif direction == 3 and row < self.row - 1 and col < self.col - 1:  # 右下
            return idx + self.col + 1
        elif direction == 4 and row < self.row - 1:  # 下
            return idx + self.col
        elif direction == 5 and row < self.row - 1 and col > 0:  # 左下
            return idx + self.col - 1
        elif direction == 6 and col > 0:  # 左
            return idx - 1
        elif direction == 7 and row > 0 and col > 0:  # 左上
            return idx - self.col - 1
        return None

    def check_and_move(self, idx):
        global saved
        row, col = idx // self.col, idx % self.col
        if self.g_direction == 0 and row == 0 and saved < 3 and self.box_is_open:  # 我要飞出去辣，但一次更新最多飞3个
            ssr = random.choice([0, 1, 2, 3]) == 0
            if ssr:
                self.box[idx] = 0
                self.snow_num -= 1
                saved += 1
                return

        new_idx = self.get_new_position(idx, self.g_direction)
        if new_idx is not None and self.box[new_idx] == 0:  # 如果新位置无雪花，直接移动
            self.box[idx], self.box[new_idx] = self.box[new_idx], self.box[idx]
        else:  # 检查左下和右下
            left_down = self.get_new_position(idx, (self.g_direction - 1) % 8)
            right_down = self.get_new_position(idx, (self.g_direction + 1) % 8)
            choices = []
            if left_down is not None and self.box[left_down] == 0:
                choices.append(left_down)
            if right_down is not None and self.box[right_down] == 0:
                choices.append(right_down)
            if choices:  # 随机选择一个可移动的方向
                new_idx = random.choice(choices)
                self.box[idx], self.box[new_idx] = self.box[new_idx], self.box[idx]
    
    def update(self):
        if self.g_direction == 4:  # 向下
            indices = [(r, c) for r in range(self.row - 1, -1, -1) for c in range(self.col)]
        elif self.g_direction == 0:  # 向上
            indices = [(r, c) for r in range(self.row) for c in range(self.col)]
        elif self.g_direction == 2:  # 向右
            indices = [(r, c) for c in range(self.col - 1, -1, -1) for r in range(self.row)]
        elif self.g_direction == 6:  # 向左
            indices = [(r, c) for c in range(self.col) for r in range(self.row)]
        elif self.g_direction == 1:  # 右上
            indices = [(r, c) for c in range(self.col - 1, -1, -1) for r in range(self.row - 1, -1, -1)]
        elif self.g_direction == 3:  # 右下
            indices = [(r, c) for c in range(self.col - 1, -1, -1) for r in range(self.row)]
        elif self.g_direction == 5:  # 左下
            indices = [(r, c) for c in range(self.col) for r in range(self.row)]
        elif self.g_direction == 7:  # 左上
            indices = [(r, c) for c in range(self.col) for r in range(self.row - 1, -1, -1)]


        global saved
        saved = 0

        for r, c in indices:
            idx = r * self.col + c
            if self.box[idx] == 1:
                self.check_and_move(idx)


class LEDMatrix:
    def __init__(self, cascaded=2):
        self.serial = spi(port=0, device=0, gpio=noop())
        self.device = max7219(self.serial, cascaded=cascaded)

    def set_contrast(self, value):
        """
        设置LED亮度级别。

        :param value: 亮度级别（0-255）。
        """
        self.device.contrast(value)

    def turn_on(self):
        """
        打开LED点阵的显示。
        """
        self.device.show()

    def turn_off(self):
        """
        关闭LED点阵的显示。
        """
        self.device.hide()

    def clear(self):
        """
        清除LED点阵的显示内容。
        """
        self.device.clear()

    def map_and_draw(self, snowbox):
        image = Image.new("1", (16, 8))

        for idx, value in enumerate(snowbox.box):
            x = idx // 8  # raw row
            y = idx % 8  # raw col

            if x < 8 and x >= 0:
                image.putpixel((y, x), value)
            elif x >= 8 and x < 16:
                image.putpixel((y + 8, x - 8), value)
            else:
                print("What???")

        self.device.display(image)


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
        self.move_servo(115)

    def servo_map(self, value, range_min, range_max):
        percent = (value - range_min) / (range_max - range_min)
        return self.servo_width_min + percent * (self.servo_width_max - self.servo_width_min)

    def move_servo(self, angle):
        duty_cycle = self.servo_map(angle, 0, 180)
        self.servo.ChangeDutyCycle(duty_cycle)

    def tap_once(self, box, matrix):
        if time.time() - self.last_tap_time >= self.tap_interval:
            box.update()
            matrix.map_and_draw(box)

            for angle in range(116, 71, -4):
                self.move_servo(angle)
                time.sleep(0.02)

            box.update()
            matrix.map_and_draw(box)

            time.sleep(0.18)

            box.update()
            matrix.map_and_draw(box)

            time.sleep(0.18)

            box.update()
            matrix.map_and_draw(box)

            for angle in range(72, 117, 4):
                self.move_servo(angle)
                time.sleep(0.02)

            self.total_taps += 1
            self.current_taps += 1
            self.last_tap_time = time.time()
            return True
        else:
            return False

    def toggle_auto(self):
        if self.keep_tapping:
            self.keep_tapping = False
        else:
            self.keep_tapping = True

    def add_tap_time(self, n):
        if isinstance(n, int) and n > 0:
            self.wait_for_tap += n

    def sub_tap_time(self):
        if self.wait_for_tap > 0:
            self.wait_for_tap -= 1

    def get_tap_time(self):
        return self.wait_for_tap

    def reset_current_taps(self):
        self.current_taps = 0

    def disp_cont(self):
        print(f">> Current taps: {self.current_taps}, Total taps: {self.total_taps}")
        print(f">> Wait for: {self.wait_for_tap} tap(s), Auto: {self.keep_tapping}")

    def get_disp_cont(self):
        return self.current_taps, self.total_taps, self.wait_for_tap, self.keep_tapping

    def cleanup(self):
        self.servo.stop()


class GY25:
    def __init__(self, name, baud_rate=115200):
        self.ser = serial.Serial(name, baud_rate)
        self.init_gy25()

    def init_gy25(self):
        self.ser.write(b'\xA5\x54')
        time.sleep(0.5)
        self.ser.write(b'\xA5\x55')
        time.sleep(0.5)
        self.ser.write(b'\xA5\x52')
        time.sleep(0.2)

    def read_gy25_data(self):
        self.ser.read_all()
        start = None
        while start != b'\xaa':
            start = self.ser.read(1)
        data = b'\xaa'
        while len(data) < 9:
                    data+=self.ser.read(1)
                    if data[-1] == 0x55 and len(data) == 8:
                        # print(data)
                        return data

    def get_orientation(self):
        gy25_data = self.read_gy25_data()
        if gy25_data is not None:
            # ypr = [x/100 for x in struct.unpack('bhhh', gy25_data)[1:]]
            ypr = []
            for b in range(1, 7, 2):
                ypr.append(int.from_bytes(gy25_data[b:b+2], "big", signed=True) /100)
            return ypr


# global
servo_controller = None
inversed = None
box = None
gy25 = None

app = flask.Flask(__name__)
# CORS(app)

@app.route('/add_tap_one')
def serve_add_tap():
    servo_controller.add_tap_time(1)
    return 'ok'

@app.route('/get_good')
def serve_get_good():
    return str(box.snow_num)


def serve():
    app.run(host='0.0.0.0', port=port)

def check_btn():
    global servo_controller, inversed, box
    while True:
        time.sleep(0.005)
        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW:
            time.sleep(0.005)
            button_state = GPIO.input(button_pin)
            if button_state == GPIO.LOW:    
                if servo_controller.keep_tapping:
                    # inversed = not inversed
                    box.box_is_open = not box.box_is_open
                else:
                    servo_controller.add_tap_time(1)
            time.sleep(0.3)


def check_ypr():
    global servo_controller, inversed, box, gy25
    while True:
        time.sleep(0.05)
        ypr = gy25.get_orientation()
        if ypr is not None:
            # print(f"P: {ypr[1]:.2f}")
            if ypr[1] >= -15 and ypr[1] <= 15:
                box.change_g(4)
            if ypr[1] >= 45 and ypr[1] <= 70:
                box.change_g(0)
            if ypr[1] >= 80 and ypr[1] <= 90:
                box.change_g(6) 
            if ypr[1] >= -40 and ypr[1] <= -20:
                box.change_g(2)
            # if ypr[1] >= 10 and ypr[1] <= 20:
            #     box.change_g(1)
            # if ypr[1] >= 35 and ypr[1] <= 45:
            #     box.change_g(5)
            # if ypr[1] >= 25 and ypr[1] <= 35:
            #     box.change_g(3) 
            # if ypr[1] >= 100 and ypr[1] <= 110:
            #     box.change_g(7)


def main():
    global servo_controller, inversed, box, gy25
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print('>> Key Setup OK!')

    player = BGMPlayer()
    music_path = "../res/ysf.mp3"
    player.load_music(music_path) 
    left_key = GPIO.input(button2_pin)
    has_played = 0
    if left_key == GPIO.LOW:
        player.play()
        has_played = 1
        pause_play = 0
    else:
        player.pause()
        pause_play = 1
    print('>> BGM Setup OK!')

    oled = OLEDCtrl()
    oled.display_status()
    print('>> OLED Setup OK!')

    matrix = LEDMatrix(cascaded=2)
    box = SnowBox(16, 8, 4)
    matrix.clear()
    matrix.set_contrast(128)

    gy25 = GY25('/dev/ttyAMA1', 115200)
    inversed = 0
    print('>> GY-25 Setup OK!')

    servo_controller = ServoController(pin=12)
    servo_controller.keep_tapping = False
    print('>> Servo Setup OK!')

    time.sleep(0.5)

    try:
        _thread.start_new_thread(check_btn, ())
        _thread.start_new_thread(check_ypr, ())
        _thread.start_new_thread(serve, ())
        while True:
            # 读取按钮状态
            print(f"[+] bgm pause: {pause_play}, auto: {servo_controller.keep_tapping}, open: {box.box_is_open}")
            print(f">> Current Merit: {box.snow_num}")
            right_key = GPIO.input(button1_pin)
            left_key = GPIO.input(button2_pin)
            print(f">> Right: {'Pressed' if right_key == GPIO.LOW else 'Released'}", end=" | ")
            print(f"Left: {'Pressed' if left_key == GPIO.LOW else 'Released'}")
            
            if right_key == GPIO.LOW:
                servo_controller.keep_tapping = True
            else:
                servo_controller.keep_tapping = False
            if left_key == GPIO.LOW:
                if not has_played:
                    player.play()
                    has_played = 1
                    pause_play = 0
                if pause_play:
                    player.pause()
                    pause_play = 0
            else:
                if not pause_play:
                    player.pause()
                    pause_play = 1

            # # 按钮控制版本的方向反转
            # if inversed:  
            #     box.change_g(0)
            # else:
            #     box.change_g(4)

            # 敲击木鱼
            if servo_controller.keep_tapping:
                result = servo_controller.tap_once(box, matrix)
                if result: box.add_snow(1)
                servo_controller.disp_cont()
            elif servo_controller.get_tap_time() > 0:
                result = servo_controller.tap_once(box, matrix)
                if result:
                    servo_controller.sub_tap_time()
                    box.add_snow(1)
                servo_controller.disp_cont()

            box.update()
            matrix.map_and_draw(box)

            oled.display_status(servo_controller, box)

            time.sleep(0.12)

    except KeyboardInterrupt:
        player.stop()
        gy25.ser.close()
        matrix.clear()
        GPIO.cleanup()
        servo_controller.cleanup()


if __name__ == "__main__":
    main()