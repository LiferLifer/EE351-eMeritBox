from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import time


def stats(oled):
    font = ImageFont.load_default()
    with canvas(oled) as draw:
        localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        draw.text((2, 5), localtime, font=font, fill=255)


def emb_show():
    serial = i2c(port=0, address=0x3C)
    oled = sh1106(serial)
    while True:
        stats(oled)
        time.sleep(1)


def main():
    serial = i2c(port=0, address=0x3C)
    oled = sh1106(serial)
    while True:
        stats(oled)
        time.sleep(1)


if __name__ == "__main__":
    main()
