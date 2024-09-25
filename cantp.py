"""
cantp.py

Thư viện xử lý giao thức CAN Transport Protocol (CanTP) cho việc gửi và nhận tin nhắn qua CAN và CANFD.
Bao gồm các chức năng quản lý các frame, kiểm soát timeout, padding, và các cơ chế truyền tin theo chuẩn CANTP.
"""
import can
import struct
import time
import random
from enum import Enum

NAByte = 0xFF                           # N/A byte của FlowControl
PADDING_BYTE = 0xFF                     # Padding byte của CAN Frame
MESSAGER_BUFFER_WAIT_LENGTH=1000        # Độ dài buffer tối đa trước khi phải gửi Waiting FlowControl
N_WFTmax = 2                            # Số lần tối đa gửi waiting FlowControl
MESSAGER_BUFFER_MAXIMUM_LENGTH=10000    # Độ dài buffer tối đa trước khi phải gửi Overflow FlowControl

# Danh sách các giá trị bậc muốn dùng để padding trong CAN Frame
PADDING_SIZES = [8, 12, 16, 20, 24, 32, 48, 64]

N_Ar = 1 # Time for transmission of the CAN frame (any N-PDU) on the receiver side
N_As = 1 # Time for transmission of the CAN frame (any N-PDU) on the sender side
N_Br = 1 # Time until transmission of the next flow control N-PDU
N_Bs = 1 # Time until reception of the next flow control N-PDU
N_Cs = 1 # Time until transmission of the next consecutive frame
N_Cr = 1 # Time until reception of the next consecutive frame

# Định nghĩa cho các loại gói tin (Packet Type)
class PCIType(Enum):
    SINGLE_FRAME = 0x00
    FIRST_FRAME = 0x10
    CONSECUTIVE_FRAME = 0x20
    FLOW_CONTROL = 0x30

# Định nghĩa cho trạng thái dòng dữ liệu (Flow Status)
class FlowStatus(Enum):
    FLOW_STATUS_CTS = 0x00
    FLOW_STATUS_WAIT = 0x01
    FLOW_STATUS_OVERFLOW = 0x02
    FLOW_STATUS_TIMEOUT = 0x03

# Các giá trị mặc định cho Block Size và STmin
class Defaults(Enum):
    BLOCK_SIZE_DEFAULT = 15
    ST_MIN_DEFAULT = 10
    TIMEOUT =1

# Các giá trị giới hạn (Maximum Values)
class MaxValues(Enum):
    CAN_CLASSIC_MAX_DATA_FRAME_LENGTH = 8                           # Số byte dữ liệu tối đa trong một gói Can Classic
    CAN_FD_MAX_DATA_FRAME_LENGTH = 64                               # Số byte dữ liệu tối đa trong một gói Can FD

    MAX_PAYLOAD_PER_CONSECUTIVE_CLASSIC_FRAME = 7                   # Số byte SDU tối đa trong một gói ConsecutiveFrame Can Classic
    MAX_PAYLOAD_PER_SINGLE_CLASSIC_FRAME = 7                        # Số byte SDU tối đa trong một gói SingleFrame Can Classic
    MAX_PAYLOAD_PER_FIRST_CLASSIC_FRAME_DATA_SMALLER_THAN_4095 = 6  # Số byte SDU tối đa trong một gói FirstFrame Can Classic khi data ít hơn 4095 byte
    MAX_PAYLOAD_PER_FIRST_CLASSIC_FRAME_DATA_BIGGER_THAN_4095 = 2   # Số byte SDU tối đa trong một gói FirstFrame Can Classic khi data nhiều hơn 4095 byte

    MAX_PAYLOAD_PER_CONSECUTIVE_FD_FRAME = 63                       # Số byte SDU tối đa trong một gói ConsecutiveFrame Can FD
    MAX_PAYLOAD_PER_SINGLE_FD_FRAME = 63                            # Số byte SDU tối đa trong một gói SingleFrame Can FD
    MAX_PAYLOAD_PER_FIRST_FD_FRAME_DATA_SMALLER_THAN_4095 = 62      # Số byte SDU tối đa trong một gói FirstFrame Can FD khi data ít hơn 4095 byte
    MAX_PAYLOAD_PER_FIRST_FD_FRAME_DATA_BIGGER_THAN_4095 = 58       # Số byte SDU tối đa trong một gói FirstFrame Can FD khi data nhiều hơn 4095 byte
     
#Class CANTP
class CanTP:
    def __init__(self, bus:can.BusABC, arbitration_id, padding=False, isFD=False):
        self.bus = bus
        self.arbitration_id = arbitration_id
        self.padding= padding
        self.isFD= isFD
    
    #Gửi 1 Frame, thêm  padding và check timeout nếu có
    def send_one_frame(self, data, timeout= Defaults.TIMEOUT.value):
        max_frame_length=MaxValues.CAN_FD_MAX_DATA_FRAME_LENGTH.value if self.isFD else MaxValues.CAN_CLASSIC_MAX_DATA_FRAME_LENGTH.value
        # Tìm giá trị padding gần nhất lớn hơn chiều dài dữ liệu hiện tại
        data_length = len(data)
        if self.padding and data_length < max_frame_length:
            # Tìm giá trị bậc lớn hơn gần nhất để padding
            nearest_padding_size = next(size for size in PADDING_SIZES if size > data_length)
            # Padding dữ liệu
            data = data + [PADDING_BYTE] * (nearest_padding_size - data_length)
        # Tạo và gửi frame CAN
        msg = can.Message(arbitration_id=self.arbitration_id, data=data, is_extended_id=False, is_fd=self.isFD)
        self.bus.send(msg, timeout=timeout)
        print(f"Message sent: {data}")

    #Gửi FlowControl
    def send_flow_control(self, flow_status=FlowStatus.FLOW_STATUS_CTS.value, block_size=Defaults.BLOCK_SIZE_DEFAULT.value, st_min=Defaults.ST_MIN_DEFAULT.value, timeout= Defaults.TIMEOUT.value):
        pci_byte = PCIType.FLOW_CONTROL.value | flow_status
        flow_control_frame = [pci_byte, block_size, st_min, NAByte, NAByte, NAByte]
        self.send_one_frame(flow_control_frame)

    #Chờ FlowControl, check timeout và trả về FlowStatus, BlockSize và Stmin
    def wait_for_flow_control(self):
        start_time = time.time()
        while True:
            # Kiểm tra timeout N_Bs
            if (time.time() - start_time) > N_Bs:
                print(f"Wait FlowControl Timeout after N_Bs={N_Bs} seconds.")
                return FlowStatus.FLOW_STATUS_TIMEOUT.value, 0, 0
            #Kiểm tra message, lấy dữ liệu FlowControl
            msg = self.bus.recv(timeout=Defaults.TIMEOUT.value)
            if msg and msg.arbitration_id == self.arbitration_id:
                data = msg.data
                pci_type = data[0] & 0xF0
                if pci_type == PCIType.FLOW_CONTROL.value:
                    flow_status = data[0] & 0x0F
                    block_size = data[1]
                    st_min = data[2]
                    return flow_status, block_size, st_min

    #Gửi tin nhắn với độ dài bất kỳ, sẽ tự động phân mảnh tin nhắn dài và xử lý các FlowControl gửi trả
    def send_message(self, data):
        try:
            total_data_length = len(data)

            max_single_frame_length=0
            if(self.isFD):
                if(total_data_length<8):
                    #1 byte PCI, 63 byte SDU
                    max_single_frame_length=MaxValues.MAX_PAYLOAD_PER_SINGLE_FD_FRAME.value 
                else:
                    #2 byte PCI, 62 byte SDU
                    max_single_frame_length=MaxValues.MAX_PAYLOAD_PER_SINGLE_FD_FRAME.value -1
            else:
                #1 byte PCI, 7 byte SDU
                max_single_frame_length=MaxValues.MAX_PAYLOAD_PER_SINGLE_CLASSIC_FRAME.value
                
            if total_data_length <= max_single_frame_length:
                #Single Frame
                sf_dl = total_data_length
                pci_byte=[]
                # Kiểm tra điều kiện để xác định số byte PCI
                if (max_single_frame_length == MaxValues.MAX_PAYLOAD_PER_SINGLE_CLASSIC_FRAME.value) | (max_single_frame_length == MaxValues.MAX_PAYLOAD_PER_SINGLE_FD_FRAME.value):
                    #1 byte PCI
                    pci_byte = [PCIType.SINGLE_FRAME.value | sf_dl]
                else:
                    #2 byte PCI
                    # pci_byte= PCIType.SINGLE_FRAME.value, sf_dl
                    pci_value = (PCIType.SINGLE_FRAME.value << 8) | sf_dl  # Kết hợp thành 16-bit giá trị
                    pci_byte = [(pci_value >> 8) & 0xFF, pci_value & 0xFF]  # Tách thành 2 byte

                payload = pci_byte + data
                self.send_one_frame(payload, timeout=N_As)
            else:
                #First Frame
                ff_dl = total_data_length
                SDU_length=0
                if ff_dl <= 4095:
                    #Data length it hon 4095 byte
                    if(self.isFD): 
                        SDU_length=MaxValues.MAX_PAYLOAD_PER_FIRST_FD_FRAME_DATA_SMALLER_THAN_4095.value
                    else:
                        SDU_length=MaxValues.MAX_PAYLOAD_PER_FIRST_CLASSIC_FRAME_DATA_SMALLER_THAN_4095.value
                    pci_bytes = [PCIType.FIRST_FRAME.value | (ff_dl >> 8), ff_dl & 0xFF]
                    payload = pci_bytes + data[:SDU_length]
                else:
                    #Data length nhieu hon 4095 byte
                    if(self.isFD): 
                        SDU_length=MaxValues.MAX_PAYLOAD_PER_FIRST_FD_FRAME_DATA_BIGGER_THAN_4095.value
                    else:
                        SDU_length=MaxValues.MAX_PAYLOAD_PER_FIRST_CLASSIC_FRAME_DATA_BIGGER_THAN_4095.value                  
                    pci_bytes = [PCIType.FIRST_FRAME.value, 0] + list(struct.pack(">I", ff_dl))
                    payload = pci_bytes[:6] + data[:SDU_length]

                sequence_number = 1
                remaining_data = data[SDU_length:] #đã gửi SDU_length byte, còn lại từ SDU_length đến hết

                self.send_one_frame(payload, timeout=N_As)

                #Consecutive Frame
                while remaining_data:
                    flow_status, block_size, st_min = self.wait_for_flow_control()
                    # print(f"flow_status={flow_status}, block_size={block_size}, st_min={st_min}")

                    start_time=time.time()

                    if flow_status == FlowStatus.FLOW_STATUS_CTS.value:
                        if(time.time()-start_time) > N_Cs:
                            #Vượt quá thời gian chờ tối đa giữa 2 lần Consecutive Frame 
                            print(f"Next Consecutive Frame Timeout after N_Cs={N_Cs} seconds.")
                            break
                        else:
                            #Không vượt quá thời gian chờ, làm mới thời gian chờ
                            start_time=time.time()
                        max_payload = MaxValues.MAX_PAYLOAD_PER_CONSECUTIVE_FD_FRAME.value if self.isFD else MaxValues.MAX_PAYLOAD_PER_CONSECUTIVE_CLASSIC_FRAME.value

                        while remaining_data:
                            SDU_size = min(max_payload, len(remaining_data))
                            pci_byte = PCIType.CONSECUTIVE_FRAME.value | (sequence_number & 0x0F)
                            cf_data = [pci_byte] + remaining_data[:SDU_size]
                            self.send_one_frame(cf_data, timeout=N_As)
                            sequence_number += 1
                            remaining_data = remaining_data[SDU_size:]

                            if (sequence_number - 1) % block_size == 0:
                                # print("Waiting for next FlowControl...")
                                break

                            time.sleep(st_min / 1000.0)
                    if flow_status == FlowStatus.FLOW_STATUS_WAIT.value:
                        print("FlowStatus: WAIT")
                    if flow_status == FlowStatus.FLOW_STATUS_OVERFLOW.value:
                        print(f"FlowStatus: OVERFLOW")
                        break
                    if flow_status == FlowStatus.FLOW_STATUS_TIMEOUT.value:
                        # print("Failed to receive FlowControl after maximum retries.")
                        break
        except Exception as e:
            print(f"An error occurred during send: {e}")

    #Chờ và đọc tin nhắn gửi tới, gửi trả các FlowControl nếu có, xử lý waiting và overflow buffer
    def receive_message(self):
        try:
            full_message = []
            expected_length = 0
            frames_received = 0
            block_size = Defaults.BLOCK_SIZE_DEFAULT.value
            st_min = Defaults.ST_MIN_DEFAULT.value
            wait_length= MESSAGER_BUFFER_WAIT_LENGTH
            start_time=0

            while True:
                msg = self.bus.recv(timeout=Defaults.TIMEOUT.value)
                if msg:
                    data = msg.data
                    pci_type = data[0] & 0xF0 
                    if pci_type == PCIType.SINGLE_FRAME.value:
                        #SINGLE FRAME
                        sf_dl = data[0] & 0x0F
                        if(sf_dl==0):
                            #Đây là gói tin FD với Datalength >8, vị trí SF_DL ở byte 1 chứ không phải byte 0
                            sf_dl=data[1]
                        if sf_dl>= MESSAGER_BUFFER_MAXIMUM_LENGTH:
                            self.send_flow_control(flow_status= FlowStatus.FLOW_STATUS_OVERFLOW.value, timeout= N_Ar)
                            print(f"Buffer OverFlow, data length:{sf_dl}, buffer length:{MESSAGER_BUFFER_MAXIMUM_LENGTH}")
                            break   
                        full_message = data[1:1 + sf_dl]
                        expected_length=data[0] & 0x0F
                        if len(full_message) >= expected_length:
                             print(f"Single message received: {full_message}")
                        break

                    elif pci_type == PCIType.FIRST_FRAME.value:
                        #FIRST FRAME
                        start_time= time.time() #đánh dấu thời điểm nhận FirstFrame
                        ff_dl=0
                        if (data[0] & 0x0F) == 0 and data[1] == 0:
                            expected_length = struct.unpack(">I", bytes(data[2:6]))[0]
                            full_message = data[6:]
                        else:
                            expected_length = ((data[0] & 0x0F) << 8) | data[1]
                            full_message = data[2:]

                        ff_dl=expected_length
                        if ff_dl>= MESSAGER_BUFFER_MAXIMUM_LENGTH:
                            self.send_flow_control(flow_status= FlowStatus.FLOW_STATUS_OVERFLOW.value, timeout= N_Ar)
                            print(f"Buffer OverFlow, data length:{ff_dl}, buffer length:{MESSAGER_BUFFER_MAXIMUM_LENGTH}")
                            break   
                        frames_received = 0
                        if (time.time() - start_time) >N_Br:
                            #Vượt quá thời gian chờ tối đa giữa FirstFrame và ConsecutiveFrame
                            print(f"First Consecutive Frame Timeout after N_Br={N_Br} seconds.")
                            break
                        else:
                            #Không vượt quá thời gian chờ, làm mới thời gian chờ và đánh dấu thời điểm gửi FlowControl CTS để gửi consecutive
                            start_time=time.time()   
                            self.send_flow_control(timeout= N_Ar)
                    elif pci_type == PCIType.CONSECUTIVE_FRAME.value:           
                        if (time.time() - start_time) >N_Cr:
                            #Vượt quá thời gian chờ tối đa giữa 2 lần Consecutive Frame 
                            print(f"Next Consecutive Frame Timeout after N_Cr={N_Cr} seconds.")
                            break
                        else:
                            #Không vượt quá thời gian chờ, làm mới thời gian chờ
                            start_time=time.time()    
                        sequence_number = data[0] & 0x0F
                        full_message += data[1:]
                        frames_received += 1               

                        if len(full_message) >= expected_length:
                            full_message=full_message[:expected_length]
                            print(f"Full message received: {full_message}")
                            break

                        if frames_received >= block_size:
                            if(len(full_message) >=wait_length):
                                wait_number = random.randint(1,N_WFTmax)
                                while wait_number!=0:
                                    self.send_flow_control(flow_status=FlowStatus.FLOW_STATUS_WAIT.value, timeout= N_Ar)
                                    print(f"Full buffer,expected length={expected_length}, buffer legnth={wait_length}, wait...\n")
                                    time.sleep(0.1)#Giả lập việc chờ wait flowcontrol
                                    wait_number-=1
                                wait_length= wait_length*2
                                frames_received = 0 
                                self.send_flow_control(timeout= N_Ar)
                            else :
                                frames_received = 0 
                                self.send_flow_control(timeout= N_Ar)
                else:
                    # print("No message Data")
                    break
        except Exception as e:
            print(f"An error occurred during receive: {e}")

