# Biên bản bàn giao phần AI V6 và bản ghép V6.1

Phạm vi bàn giao: model 6–8–3, RTL AI, lượng tử hóa C, bộ kiểm thử, dữ liệu/provenance và bản ghép CPU–AI–MAC tham chiếu. Bản V6.1 giữ nguyên model/firmware V6 và sửa tầng RX lấy mẫu cạnh xuống. Đã đạt kiểm chức năng và timing nội bộ sau Place & Route của đúng source này. Đây chưa phải biên bản nghiệm thu Ethernet/chặn trên bo thật.

## Định danh

- Model: `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`.
- Firmware bo: `492eebd36fd67625596ef5f72cfc9bd408649e39e0f0d693b5503ffd40b684a2`.
- Source RX sửa: `4c6e29a8403965f7347eda1dac97f510353fa6ac35edc4ef6d8b2a309749b7ac`.
- Top: `gowin_top`, device `GW1NR-LV9QN88PC6/I5`, SELFTEST=2, REF_METER=0.
- Báo cáo người dùng: Gowin V1.9.8.11 Education, tạo ngày06/11/2026 lúc13:19:48 theo đồng hồ máy tạo báo cáo. Chi tiết/hash ở `GOWIN_V6_1_REVIEW.json`.

## Kết quả đã có

| Hạng mục | Kết quả |
|---|---|
| RTL AI qua Wishbone | PASS3.762vector; scores có dấu, byte enable, START/busy và ABORT |
| CPU chạy firmware | POST37/37,36lần suy luận và1cửa sổ rỗng bỏ qua |
| Feature tham chiếu | PASS5cửa sổ, cardinality và lượng tử hóa |
| RX so với V6 cũ | PASS40khung/24.273byte mỗi chế độ cạnh;30CRC tốt,10CRC lỗi; cạnh xuống trễ đúng1chu kỳ |
| MAC và hệ thống | PASS byte/FCS hai chiều, khung dài, CRC lỗi, demo40giây, SYN/scan/TTL và37trace |
| Gowin sau P&R |0setup lỗi,0hold lỗi ở27/50/50MHz |
| Chạy trên bo thật | Chưa thực hiện |

| Clock | Yêu cầu MHz | Fmax STA MHz |
|---|---:|---:|
| clk_27m |27|33,655|
| a_ref_clk |50|92,664|
| b_ref_clk |50|78,935|

Slack setup nhỏ nhất trong các đường được báo cáo là+3,666ns; hold+0,482ns. Logic5372/8640(63%),register3204/6693(48%),BSRAM15khối(58%),DSP1,0latch. Tần số trên là số STA theo ràng buộc, không phải throughput đo trên mạng.

## Người nhận và file sử dụng

| Phần việc | Nội dung giao |
|---|---|
| Người1 — CPU/bus/firmware/top | Nguyên thư mục gói, `sources.f`, `rtl/wb_ai_regs.v`, `fw/`, `CHUAN_BI_GOWIN.py` |
| Người phụ trách P3 | `docs/HOP_DONG_GHEP_V6.md`, chuẩn6đặc trưng/cửa sổ/receiver và các test feature; thay module tham chiếu bằng module chính thức rồi kiểm lại |
| Người phụ trách MAC/PHY | `rtl/part4_eth/`, test RX/MAC, cảnh báoPR1014, overflow và xác nhận dây/clock/PHY |
| Phần AI | `rtl/part2_ai/`, `fw/part2/`, `training/frozen/`, nguồn/cache/PCAP/CSV trong `training/` |

Giao nguyên thư mục giúp giữ cùng bộ model/RTL/header/firmware. Không cần train lại để nhận bàn giao này. Khi đổi thư mục trên Windows, chạy `python CHUAN_BI_GOWIN.py` để tạo đường dẫn firmware đúng máy đó; mở `gateway_phan1_v6_1.gprj`, top `gowin_top`. Source/firmware/config/chân/clock thay đổi thì cần build và kiểm lại. Không có bitstream `.fs` trong gói tải về; người dùng đang có file do Gowin sinh trong project đã kiểm.

## Các việc còn lại trước nghiệm thu trên mạng thật

1. Xác nhận Tang Nano9K, cách nối hai LAN8720, nguồn/điện áp và nguồn clock/pha thực. PR1014 ởclockB vẫn còn. SDC hiện chỉ có3clock và async groups; chưa có ngân sách timing I/O theo PHY/dây. Cần rà soát CDC và reset, không coi0setup/hold nội bộ là đã xác nhận các phần này.
2. Chạy trên bo, ghi UART115200/8N1, xác nhận hashV6 và POST37/37. REF_METER=0 trong wrapper hiện tại; không suy ra clockPHY đã được đo từ kết quả mô phỏng.
3. Người1 chốt IP receiver /32 và whitelist. Mặc định bảo vệ192.168.10.2, whitelist.2/.20; boot DETECT. Chỉnh `fw/config.h` phải build lại firmware và kiểm lại.
4. Đo hai chiều Ethernet, MQTT/ARP/cảm biến, CRC/overflow/drop. Prototype MAC đã quan sát overflow25 trong bài burst, chưa được sửa thành zero-loss.
5. Tích hợp P3 chính thức, kiểm SYN/scan/TTL/gỡ chặn và reconnect hợp lệ bằng PCAP+UART trên bo. Thu test độc lập nếu cần kết luận độ phát hiện trên lưu lượng mới.

## Giới hạn model giữ nguyên

Nguồn là Normal IoT-23, SYN capture34 IoT-23 và vertical scan Chris Sanders cùng các biến thể đã công bố. Tập học gốc có12lỗiNormal; development cùng nguồn có1missSYN; lab lịch sử218/219 với1Normal nhậnScan. Các số này không phải kiểm thử mới độc lập. Vẫn giữ nhãn/xung đột và cửa sổ thưa trong dữ liệu/báo cáo. Gói đủ để bàn giao phần AI và tích hợp tham chiếu; chưa xác nhận chặn tự động trên mạng thật.

## Thiết bị hiện có và bước kế tiếp

Người dùng xác nhận có Tang Nano9K, chưa nối đủ haiLAN8720. Gói bàn giao có helperdemo riêng (CHUAN_BI_DEMO_GOWIN.py/topgowin_demo_top,clock27MHz,12chân) để chuẩn bị kiểmCPU–AI quaUSB/UART với trafficheader nội bộ. Xem HUONG_DAN_DEMO_TREN_BO.md. Timing demo cần kiểm riêng trước nạp; không lấy kết quả MAC hoặc mô phỏng để tuyên bố bo đã PASS. PhầnMAC không đổi source/chân/SDC. Khi chuyển giao chứng từ tool cho nhóm, gửi kèm BAO_CAO_GOWIN_V6_1.zip do nhóm đã tạo; SHA được ghi trong GOWIN_V6_1_REVIEW.json.
