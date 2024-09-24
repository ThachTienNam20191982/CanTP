# CanTP

# Thư viện Giao thức Truyền tải CAN (CanTP) và các ví dụ

Repository này bao gồm một thư viện Python triển khai Giao thức Truyền tải CAN (CanTP) và các chương trình ví dụ minh họa cách gửi và nhận tin nhắn qua mạng CAN. Repository bao gồm:

- `cantp.py`: Thư viện CanTP, xử lý việc quản lý các frame CAN, timeout, padding và các tính năng khác của giao thức.
- `main.py`: Chương trình ví dụ mô phỏng việc truyền tin nhắn trên bus CAN ảo (không yêu cầu phần cứng).
- `sender.py`: Chương trình gửi tin nhắn CAN với phần cứng hỗ trợ.
- `receiver.py`: Chương trình nhận tin nhắn CAN với phần cứng hỗ trợ.

## Cấu trúc của repository

- **cantp.py**:  
  Đây là thư viện chính triển khai Giao thức Truyền tải CAN. Nó bao gồm các chức năng:
  - Phân chia các tin nhắn lớn thành các frame CAN nhỏ hơn.
  - Thêm padding để đảm bảo các frame CAN tuân thủ các yêu cầu của giao thức.
  - Kiểm soát luồng (flow control)
  - Quản lý timeout cho việc truyền và nhận tin nhắn.

- **main.py**:  
  Đây là chương trình ví dụ mô phỏng việc gửi và nhận tin nhắn trên một bus CAN ảo. Chương trình này không yêu cầu phần cứng CAN thực tế và sử dụng thư viện `cantp` để minh họa hoạt động của giao thức trong môi trường ảo.

- **sender.py**:  
  Chương trình sử dụng thư viện `cantp` để gửi tin nhắn qua mạng CAN thực tế. Yêu cầu phần cứng CAN để hoạt động, thường được sử dụng trong các kịch bản thực tế khi cần truyền tin qua mạng CAN.

- **receiver.py**:  
  Chương trình sử dụng thư viện `cantp` để nhận tin nhắn từ mạng CAN thực tế. Yêu cầu phần cứng CAN, và nó cho thấy cách các tin nhắn CAN được nhận, phân đoạn và ghép lại.
