# Nạp SRAM và đọc UART cho demo V6.1 trên Tang Nano9K

Báo cáo demo người dùng gửi đã được đối chiếu: đúng model V6/firmware, source và constraints; Gowin V1.9.8.11 Education, top `gowin_demo_top`, device GW1NR-LV9QN88PC6/I5. P&R tạo ngày06/11/2026 lúc20:27:21 theo đồng hồ máy lập báo cáo. Clock27MHz có FmaxSTA35,820MHz,0setup và0hold lỗi; slack setup được báo cáo nhỏ nhất+9,119ns,hold+0,438ns. Logic4854/8640(57%),register2917/6693(44%),BSRAM13khối(50%),DSP1,0latch,12I/O.

Project demo có trafficheader sinh bên trong FPGA, không xuất các chânRMII. Không có PR1014 trong logP&R demo vì không còn clockPHY hoạt động. Điều này không thay thế kiểm PHY/clock/CDC của projectMAC. Xem `reports/V6_1_DEMO_GOWIN_REVIEW.json` để đối chiếu số và hash. Chưa có bằng chứng bo đã chạy cho đến khi nhận UART/ảnh nạp.

## 1. Kết nối kit để thử riêng CPU–AI

Tắt/rút nguồn trước khi tháo các dây GPIO đang nối dở đến LAN8720/ngoại vi. Bắt đầu với TangNano9K chỉ nối cápUSB có truyền dữ liệu vào Windows; chưa cần LAN8720 hay OLED. Giữ đúng fileCST của demo đã kiểm, không đổi chân/điện áp khi thử.

## 2. Mở Gowin Programmer

Trong Gowin IDE, dùng `Tools → Programmer`, hoặc mở ứng dụng Gowin Programmer từ Windows. Chọn/quét cápUSB và dùng `Scan Device` để nhận đúng kit GW1NR-9C/TangNano9K. Nếu không nhận được cáp/thiết bị, gửi ảnh cửa sổ Programmer để xác định đúng cấu hình/driver theo thiết bị thực tế.

## 3. Chọn file và nạp SRAM

Trong thư mục dự án demo vừa build, mở `impl\pnr\`, tìm file `.fs` mới. Tên dự kiến:

```text
impl\pnr\gateway_phan1_v6_1_demo.fs
```

Chọn file này ở mục File/Programming File của dòng thiết bị. Ở Operation, chọn mục nạpSRAM (`SRAM Program` hoặc tên tương đương `SRAM Erase, Program` theo phiên bản). Chạy `Program/Start` và đợi thông báo thành công.

Dùng đúng `.fs` của projectdemo; firmware.hex là dữ liệu nhúng trong bitstream và PCAP/CSV không phải file nạp FPGA. Lần thử này dùng SRAM tạm thời; không cần ghi Flash. Sau nạp, giữUSB để cấu hìnhSRAM còn hoạt động. NhấnS2 chỉ reset CPU theo thiết kế; rút nguồn làm mất cấu hìnhSRAM và có thể trở về nội dungFlash cũ.

## 4. Tìm cổng COM và mở UART

Mở `Device Manager → Ports (COM & LPT)` để xem cổngCOM của kit. Dùng terminal nối tiếp sẵn có hoặc PuTTY/TeraTerm:

- Connection type:Serial; Serial line:cổngCOM thực tế, ví dụCOM5.
- Speed/Baud:115200.
- Data bits:8; Stop bits:1; Parity:None; Flow control:None.

Trong PuTTY, các mục khung truyền nằm ở `Connection → Serial`; ghi log có thể chọn `Session → Logging → All session output`, tên `uart_demo_v6_1.log`. Mở terminal, sau đó nhấnS2 để thấy log từ đầu. Không ngắtUSB giữa nạp và mở terminal.

## 5. Đọc kết quả đầu tiên

Mong đợi có:

```text
# AI V6 SHA256 3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515
# POST OK: ... AI 37/37 vector, LAT 86 chu ky ...
$MODE,DETECT*28
$IDS,...
```

Phần đầu dòngIDS là `$IDS,win,cls,alert,pkt,...`; `cls=0`Normal,1SYN flood,2Vertical scan. Ghi ít nhất40giây sau reset để thấy kịch bản một vòng:0–2yên lặng,2–5Normal,5–11SYN,11–19Normal,19–24scan,24–27Normal,27–31SYN giảIP,31–35Normal rồi lặp lại. Đây là các header nội bộ, không phải phát lại PCAP hay test mạng độc lập.

Vì không nốiOLED/PHY, dòng `OLED KHONG tra loi` và `REF_CLK A=0/B=0 ... LOI` là dự kiến trong demo (REF_METER=0/đầu vàoPHY nối0). Đánh giá theo hash/POST/IDS và tình trạngCPU; không coi các dòng này là phép đo PHY. Sáu LEDuser được thiết kế tắt khi không trap.

## 6. Thử policy sau khi đã thấy POST/IDS

NhấnS1 ngắn khoảng0,2–0,5giây để đổi DETECT sang BLOCK. Có thể thấy `$MODE,BLOCK` và `$BLK` cho192.168.10.50/.51 khi đủ hai cửa sổ xác nhận. Nhấn ngắn lại về DETECT và xóa danh sách chặn. Giữ từ2giây là thao tác bật/tắt giới hạnSYN lớp2. Firmware bo dùng TTL60giây và traffic lặp lại, không lấy thời điểmgỡ chặn6giây của một số mô phỏng làm tiêu chí ở đây.

## 7. Gửi bằng chứng

Gửi ảnh Programmer báo thành công và file `uart_demo_v6_1.log` (hoặc ảnh terminal chứa hash/POST và các dòngIDS0/1/2). Có thể gom log cùng báo cáo bằng helper có sẵn:

```text
python THU_BAO_CAO_DEMO.py --uart "duong_dan_thuc_te_den_uart_demo_v6_1.log"
```

Đổi tên ZIP báo cáo cũ trước khi gom lần mới. Khi nhận kết quả thực tế mới xác nhận phầnCPU–AI đã chạy trên bo; Ethernet thật, haiLAN8720, P3 chính thức và hiệu quảphát hiện độc lập vẫn cần kiểm riêng.
