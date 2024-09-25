"""
sender.py

Chương trình sử dụng thư viện CanTP (cantp.py) để gửi tin nhắn qua mạng CAN.
Yêu cầu phần cứng CAN hỗ trợ để thực hiện việc truyền tin nhắn.
"""

import can
import time
import threading
from cantp import CanTP

# Tạo bus CAN ảo
bus1 = can.interface.Bus(interface='neovi', channel=1, bitrate=1000000)

# Tạo đối tượng CanTP cho bus1
cantp_sender = CanTP(bus1, arbitration_id=0x123, padding=False, isFD=False)

# Cờ để dừng luồng
stop_flag = False

def send_message():
    """Gửi một tin nhắn từ bus sau khi nhập dữ liệu từ người dùng"""
    global stop_flag  # Để có thể thay đổi giá trị cờ từ trong luồng
    while not stop_flag:
        # Nhập dữ liệu từ người dùng
        string_to_send = input("Nhập string muốn gửi (hoặc Enter để dừng): ")

        # Kiểm tra nếu chuỗi nhập rỗng, dừng gửi tin nhắn
        if string_to_send.strip() == "":
            stop_flag = True
            break

        # Gửi tin nhắn sau khi mã hóa thành bytes
        cantp_sender.send_message(list(string_to_send.encode('utf-8')))
        
        time.sleep(2)  # Nghỉ 2 giây giữa các lần gửi

# Tạo luồng cho việc gửi tin nhắn
send_thread = threading.Thread(target=send_message)

# Bắt đầu luồng
send_thread.start()

# Chờ cho luồng dừng
send_thread.join()

# Tắt bus
bus1.shutdown()

print("End of simulation")
