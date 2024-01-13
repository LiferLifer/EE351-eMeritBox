from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from PIL import Image, ImageDraw, ImageFont
import time, random

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


if __name__ == "__main__":
    controller = LEDMatrix(cascaded=2)
    box = SnowBox(16, 8, 4)

    try:
        controller.clear()
        controller.set_contrast(128)
        while True:
            # if box.g_direction == 4:
            #     box.add_snow(1)
            # box.update()
            # controller.map_and_draw(box)
            # print(box.snow_num)
            # time.sleep(0.1)
            # if box.snow_num == 32:
            #     box.change_g(0)
            # elif box.snow_num == 0:
            #     box.change_g(4)

            box.add_snow(1)
            box.update()
            controller.map_and_draw(box)
            time.sleep(0.1)
            if box.snow_num == 32:
                box.change_g(3)

    except KeyboardInterrupt:
        controller.clear()
