# 用法: python upgrade_host.py COM口 bin文件 目标区(1=App1, 2=App2)
# 发完帧后自动回读 Boot 的调试输出（USART6 TX / PC6）
import serial, sys, time

def crc16(data):                     # CCITT 0x1021, 初值 0xFFFF —— 和 Boot 一致
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc




port, binfile, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = open(binfile, 'rb').read()
crc = crc16(data)
frame = bytes([0xAA, 0x55, target]) + len(data).to_bytes(2, 'little') + data + crc.to_bytes(2, 'little')
print(f"发送 {len(data)} 字节, CRC=0x{crc:04X}, 目标 App{target}")

ser = serial.Serial(port, 115200, timeout=0.2)
ser.reset_input_buffer()              # 丢弃残留数据

# 分小块发帧，防 Boot 环形缓冲溢出
for i in range(0, len(frame), 128):
    ser.write(frame[i:i+128])
    time.sleep(0.005)

# 回读 Boot 调试输出，最多等 12 秒（擦除 S2+S3+S7 要几秒）
print("—— 等待 Boot 调试输出（最多12秒）——")
t_end = time.time() + 100
buf = b''
while time.time() < t_end:
    b = ser.read(1)
    if b:
        buf += b
        if b == b'\n':                # 收到换行就打印一行
            print("RX:", buf.decode('ascii', errors='replace').rstrip())
            buf = b''
    else:
        time.sleep(0.05)
if buf:
    print("RX:", buf.decode('ascii', errors='replace').rstrip())
ser.close()
print("—— 结束 ——")
