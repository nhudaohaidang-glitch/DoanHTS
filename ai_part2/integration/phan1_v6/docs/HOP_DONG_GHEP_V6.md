# Hợp đồng AI V6 cho nhóm tích hợp

Phần 2 bàn giao model, core RTL, bộ lượng tử hóa C, vector và báo cáo. Phần 1 giữ CPU/bus/firmware điều phối. P3 cần cung cấp parser, bộ đếm đặc trưng và filter chính thức; các file `rtl/stubs/` trong gói là tham chiếu có logic, chưa phải module P3 đã nghiệm thu. Phụ trách MAC/PHY hoàn thiện đường Ethernet và overflow. Người tích hợp top chốt chân, clock, reset/CDC và timing trên bo.

## Sáu đặc trưng

Chỉ tính IPv4 ingress tới đúng receiver /32 được bảo vệ, mỗi cửa sổ 1 giây cùng mốc thời gian, không gom mọi đích thành một mẫu. Bỏ phân mảnh và gói không đủ IP Total Length. Thứ tự raw:

1. `packet_count`: số gói.
2. `mean_ip_bytes`: floor(tổng IPv4 Total Length / số gói), không dùng độ dài Ethernet.
3. `syn_ratio_q127`: floor(127 × số TCP SYN không ACK / số gói); điều kiện flags & 0x12 == 0x02.
4. `src_count`: số IP nguồn phân biệt chính xác.
5. `dst_count`: số IP đích phân biệt (1 trong receiver /32).
6. `dst_port_count`: số cổng đích TCP/UDP phân biệt; không đếm ICMP như một cổng.

Lượng tử hóa `q[i]=min(127,raw[i]//divisor[i])`, divisors `[8,2,1,1,1,1]`. Bộ đếm cardinality tham chiếu đếm chính xác tới 128 rồi bão hòa, cho cùng q0..127 cần thiết; không thay bằng bitmap/hash ước lượng chưa kiểm. N=0 bỏ suy luận. N=1..7 vẫn suy luận dù q0=0.

CPU nên truyền tổng bytes và số SYN thực cho `ai_v6_prepare_window()`; không lấy phần trăm đã làm tròn từ UART để dựng lại raw. Gói 48bit: q0 ở bit7:0, q5 ở47:40. Không nhận PCAP/CSV trực tiếp vào chân core.

## Giao tiếp

Core: `clk,rst_n,start,feat[47:0]`; `busy,done,class_id,scores` giữ theo module. 84 chu kỳ core, wrapper đo 86; không phải độ trễ toàn đường trích/chặn. Trọng số int8 có dấu, bias/accumulator int32, hidden ReLU bão hòa127, score int16 có dấu. Quy tắc tie argmax chọn class thấp trước.

Wishbone AI base `0x30000000`:

| Offset | Nội dung |
|---|---|
| +0x00 | STATUS đọc: bit0 BUSY, bit1 DONE |
| +0x04 | CTRL ghi: bit0 START, bit1 ABORT |
| +0x08 | Feature low32 |
| +0x0c | Feature high16 |
| +0x10 | Kết quả class |
| +0x14/+0x18/+0x1c | Scores0/1/2, đọc signed đúng sign extension |
| +0x20 | LAT |

DONE được chốt; START lúc busy bị bỏ qua. ABORT dừng giao dịch chờ, không reset tức thời core. Dùng code và testbench đi kèm thay cho tự suy diễn cách acknowledge. Lớp0 Normal,1 SYN flood,2 Vertical scan.

Một `class_id` không xác định được IP tấn công. Firmware dùng thông tin nguồn nghi ngờ đã xác nhận, whitelist, mức tải tối thiểu, hai cửa sổ và TTL. Đếm nhiều cổng tổng hợp trong receiver không tự chứng minh một nguồn đã vertical scan. Cần đối chiếu logic gán nguồn của P3 khi thay module.

RAM16KB dùng khoảng12,9KB code/data/BSS; phần còn lại cho stack, chưa đo high-water. AI V6 chưa có báo cáo timing top sau P&R hoặc đo trên bo. Cần nộp các báo cáo đó cùng UART/hash/PCAP thực để chốt nghiệm thu phần cứng.
