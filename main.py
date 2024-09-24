"""
main.py

Chương trình chính sử dụng thư viện CanTP (cantp.py) để mô phỏng việc gửi và nhận tin nhắn qua CAN bus ảo.
Chạy trong môi trường virtual bus, không yêu cầu phần cứng CAN thực tế.
"""

import can
import threading
import time
from cantp import CanTP

# Tạo bus CAN ảo cho gửi và nhận
bus_sender   = can.interface.Bus(interface='virtual', channel=1, bitrate=1000000)
bus_receiver = can.interface.Bus(interface='virtual', channel=1, bitrate=1000000)

# Tạo đối tượng CanTP cho việc gửi và nhận
cantp_sender = CanTP(bus_sender, arbitration_id=0x123, padding=False, isFD=False)
cantp_receiver = CanTP(bus_receiver, arbitration_id=0x123, padding=False, isFD=False)

# Cờ để dừng các luồng
stop_flag = False

def send_message():
    """Gửi một tin nhắn từ bus sau khi nhập dữ liệu từ người dùng"""
    global stop_flag
    while not stop_flag:
        string_to_send = input("Nhập string muốn gửi (hoặc Enter để dừng): ")

        # Kiểm tra nếu người dùng nhập "STOP" để dừng chương trình
        if string_to_send.strip() == "":
            stop_flag = True
            break

        # Gửi tin nhắn nếu không phải "STOP"
        cantp_sender.send_message(list(string_to_send.encode('utf-8')))
        time.sleep(1)

def receive_message():
    """Nhận tin nhắn từ bus"""
    global stop_flag
    while not stop_flag:
        # Nhận tin nhắn từ bus
        message = cantp_receiver.receive_message()
        if message:
            print("Nhận tin nhắn:", message)

# Tạo luồng cho việc gửi và nhận tin nhắn
send_thread = threading.Thread(target=send_message)
receive_thread = threading.Thread(target=receive_message)

# Bắt đầu các luồng
send_thread.start()
receive_thread.start()

# Chờ cho các luồng kết thúc
send_thread.join()
receive_thread.join()

# Tắt bus
bus_sender.shutdown()
bus_receiver.shutdown()

print("End of simulation")
