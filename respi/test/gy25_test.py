import struct
import serial
import time

# 打开串口连接到GY-25
ser = serial.Serial('/dev/ttyAMA1', 115200)  # 根据实际情况更改串口名称

def init_gy25():
    ser.write(b'\xA5\x54')
    time.sleep(1)
    ser.write(b'\xA5\x55')
    time.sleep(1)
    ser.write(b'\xA5\x52')

def read_gy25_data():
    ser.read_all()
    start = None
    while start != b'\xaa':
        start = ser.read(1)
    data = b'\xaa'
    while len(data) < 9:
                data+=ser.read(1)
                if data[-1] == 0x55 and len(data) == 8:
                    print(data)
                    return data

try:
    init_gy25()  # 初始化GY-25模块
    while True:
        gy25_data = read_gy25_data()
        if gy25_data is not None:
            # ypr = [x/100 for x in struct.unpack('bhhh', gy25_data)[1:]]
            ypr = []
            for b in range(1, 7, 2):
                ypr.append(int.from_bytes(gy25_data[b:b+2], "big", signed=True) /100)
            print(f"YPR: {ypr[0]:.2f}\t{ypr[1]:.2f}\t{ypr[2]:.2f}")

        # print(ser.read(1))

        time.sleep(0.5)

except KeyboardInterrupt:
    ser.close()  # 在程序退出时关闭串口连接
    print("程序已结束，关闭GY-25串口连接")
