# Thử CPU–AI V6 trên Tang Nano 9K khi chưa nối đủ LAN8720

Nhóm hiện có Tang Nano9K nhưng chưa nối đủ hai LAN8720. Có thể kiểm POST và quan sát dự đoán Normal/SYN/scan bằng bộ tạo header có sẵn chạy bên trong FPGA. Đây là thử CPU–AI trên bo; không phát gói ra dây Ethernet, không phát lại PCAP IoT-23/Chris Sanders và không phải test phát hiện độc lập.

## 1. Tạo project demo riêng trên Windows

Giải nén gói bàn giao vào thư mục mới. Chạy file `CHUAN_BI_DEMO_GOWIN.py` trong gói:

```text
python CHUAN_BI_DEMO_GOWIN.py
```

Nếu CMD đang ở chỗ khác: giữ Shift, nhấn chuột phải vào file, Copy as path; gõ `python ` rồi Ctrl+V và Enter. Dùng `py` thay `python` nếu đó là launcher đã hoạt động trên máy bạn.

Mở **gateway_phan1_v6_1_demo.gprj**, chọn top **gowin_demo_top**, device **GW1NR-LV9QN88PC6/I5**. Chạy Synthesize rồi Place & Route. Demo chỉ dùng clock27MHz và12chân clock/reset/nút/UART/OLED/LED; không xuất chân RMII. Header được tạo nội bộ với SELFTEST=1, REF_METER=0. Model và `fw/firmware.hex` V6 giữ nguyên. Mặc định UART115200, một cửa sổ1giây thật và TTL60giây.

Project/wrapper/chân/SDC của demo tách riêng khỏi project MAC đã đạt timing. Kết quả P&R của project MAC không thay thế P&R của project demo. Đừng chạy helper MAC với `--mode demo` để chuẩn bị bài này; helper demo riêng giữ nguyên project MAC để đối chiếu.

Gom báo cáo demo:

```text
python THU_BAO_CAO_DEMO.py
```

Gửi **BAO_CAO_DEMO_V6_1.zip** để kiểm timing/chân của đúng bản demo trước khi thử nạp bo. Collector này chỉ gom báo cáo có tên project demo; không lẫn báo cáo MAC cũ.

## 2. Chuẩn bị thử bo sau khi báo cáo demo được kiểm

Để thử bo đơn lẻ, tắt/rút nguồn trước khi tháo các dây GPIO đang nối dở tới LAN8720 và ngoại vi. Bắt đầu với kit chỉ nối cáp USB có truyền dữ liệu vào Windows. OLED không bắt buộc.

Trong Gowin Programmer, quét nhận đúng kit Tang Nano9K/GW1NR-9C, chọn file `.fs` mới của project demo trong `impl/pnr/` (thường là `gateway_phan1_v6_1_demo.fs`). Lần thử đầu dùng thao tác nạp SRAM; cấu hình này mất khi tắt nguồn. Bước này chưa ghi Flash lâu dài. Nếu Programmer không nhận đúng thiết bị/cáp, lưu ảnh thông báo để xử lý theo thiết bị thực tế.

File nạp FPGA là `.fs` do Gowin sinh. Firmware C `fw/firmware.hex` đã được nhúng khi tổng hợp; PCAP/CSV là dữ liệu phục vụ chuẩn bị/kiểm model, không đưa trực tiếp vào Programmer.

## 3. Quan sát UART

Mở terminal nối tiếp (ví dụ Tera Term/PuTTY/Serial Monitor), chọn cổng COM của kit,115200baud,8data bits,no parity,1stop bit,no flow control. Mở terminal trước rồi nhấn S2/reset để xem lại từ đầu. S2 được map vào `rst_n` pin4 theo CST; S1/key là pin3.

Kết quả mong đợi gồm:

```text
# AI V6 SHA256 3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515
# POST OK: ... AI 37/37 vector, LAT 86 chu ky ...
$MODE,DETECT*28
$IDS,...
```

Trong `$IDS`, thứ tự đầu dòng là `$IDS,win,cls,alert,pkt,...`. Class0=Normal,1=SYN flood,2=vertical scan. Ghi log ít nhất một chu kỳ khoảng35giây; nếu bắt đầu giữa chu kỳ, ghi70–90giây. Các IP192.168.10.2/.20/.50/.51 trong log là header do bộ tạo nội bộ sinh, không cần đặt IP Windows trùng các địa chỉ này.

| Thời gian từ reset, gần đúng | Lưu lượng nội bộ |
|---|---|
|0–2giây|Yên lặng|
|2–5giây|Normal|
|5–11giây|SYN flood|
|11–19giây|Normal|
|19–24giây|Vertical scan|
|24–27giây|Normal|
|27–31giây|SYN giả IP, bài phụ về policy|
|31–35giây|Normal, rồi lặp lại|

Để quan sát policy, nhấn S1 ngắn khoảng0,2–0,5giây sau POST để đổi DETECT sang BLOCK. Khi có đủ hai cửa sổ xác nhận có thể thấy `$BLK` cho.50/.51. Nhấn ngắn lần nữa về DETECT và xóa danh sách chặn. Giữ S1 từ2giây là thao tác khác: bật/tắt giới hạn SYN lớp2. Bản firmware thật dùng TTL60giây, không phải6giây như một số bài mô phỏng; lưu lượng lặp lại có thể làm thời điểm gỡ chặn khác bài40giây cũ.

Nếu không nối OLED, dòng `OLED KHONG tra loi` là dự kiến. Trong demo không có clockPHY, các số `REF_CLK A=0/B=0` hoặc thông báo LOI tương ứng không phải phép kiểm clockLAN8720; hai đầu vào được nối0 và REF_METER=0. Các tiêu chí chính của bài này là hash, POST37/37, có `$IDS` với ba class theo kịch bản và CPU không báo lỗi/trap. Sáu LED được thiết kế tắt khi CPU không trap.

## 4. Gửi bằng chứng chạy bo

Lưu log UART thành file văn bản. Có thể gửi riêng log hoặc gom cùng báo cáo demo bằng:

```text
python THU_BAO_CAO_DEMO.py --uart "duong_dan_thuc_te_den_file_uart.log"
```

Nếu ZIP báo cáo cũ tồn tại, đổi tên bản cũ trước khi gom lần mới. Ảnh Programmer báo thành công và đoạn UART chứa hash/POST/class giúp đối chiếu. Chưa coi việc demo thành công là MAC/PHY/chặn mạng thật đã hoàn thành; khi nối đủ LAN8720, dùng project MAC và kiểm clock/CRC/overflow, MQTT/ARP, traffic hai chiều và P3 chính thức.
