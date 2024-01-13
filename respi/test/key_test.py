import RPi.GPIO as GPIO
import time

# 设置GPIO模式
GPIO.setmode(GPIO.BCM)

# 定义连接按钮的GPIO引脚
button1_pin = 19  # Right_Key
button2_pin = 26  # Left_Key

# 设置GPIO引脚为输入模式，并启用上拉电阻
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    while True:
        # 读取按钮状态
        button1_state = GPIO.input(button1_pin)
        button2_state = GPIO.input(button2_pin)

        # 打印按钮状态
        print(f"Right: {'Pressed' if button1_state == GPIO.LOW else 'Released'}")
        print(f"Left: {'Pressed' if button2_state == GPIO.LOW else 'Released'}")

        # 等待一小段时间再次检测
        time.sleep(2)
except KeyboardInterrupt:
    # 捕获Ctrl+C，清理并退出
    GPIO.cleanup()
