"""
receiver.py

Chương trình sử dụng thư viện CanTP (cantp.py) để nhận tin nhắn qua mạng CAN.
Yêu cầu phần cứng CAN hỗ trợ để thực hiện việc nhận tin nhắn.
"""

import can
import threading
from cantp import CanTP

# Tạo bus CAN ảo
bus2 = can.interface.Bus(interface='neovi', channel=1, bitrate=1000000, receive_own_messages =False)

# Tạo đối tượng CanTP cho bus2
cantp_receiver = CanTP(bus2, arbitration_id=0x100, padding=True, isFD=True)

# Cờ để dừng luồng
stop_flag = False

def receive_message():
    """Nhận tin nhắn từ bus"""
    global stop_flag
    while not stop_flag:
        # Nhận và xử lý tin nhắn từ bus
        message = cantp_receiver.receive_message()
        if message:
            print("Nhận tin nhắn:", message)

def wait_for_enter():
    """Dừng nhận tin nhắn khi nhấn Enter"""
    global stop_flag
    input("Nhấn Enter để dừng...\n")
    stop_flag = True

# Tạo luồng cho việc nhận tin nhắn
receive_thread = threading.Thread(target=receive_message)

# Tạo luồng để dừng khi nhấn Enter
input_thread = threading.Thread(target=wait_for_enter)

# Bắt đầu các luồng
receive_thread.start()
input_thread.start()

# Chờ cho luồng nhận tin nhắn dừng
receive_thread.join()
input_thread.join()

# Tắt bus
bus2.shutdown()

print("End of simulation")
