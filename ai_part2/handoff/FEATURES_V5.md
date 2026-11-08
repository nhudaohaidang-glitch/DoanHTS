# Hợp đồng ghép V5 — model đã chốt

Model SHA256: `688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e`.
Kiến trúc 6–8–3; divisors `[8,2,1,1,1,1]`; shift1=5, shift2=0.
Các trọng số đã được nhúng trong `ai_core_model_v5.v`. Chỉ đưa một module
`ai_core` vào project top; thay stub/core cũ trong danh sách source.

## Phạm vi thống kê

Một đích IPv4 /32 được bảo vệ, chiều ingress tới đích này, mỗi cửa sổ 1 giây.
Normal được trích riêng cho từng đích nhận; SYN/scan dùng đúng đích và khoảng
thời gian đã kiểm chứng. Model không nhận địa chỉ IP làm đầu vào. Không gom
toàn bộ nhiều đích trong mạng thành một cửa sổ rồi coi đó là cùng contract.

Cần thống nhất mốc bắt đầu cửa sổ/reset với Python khi đối chiếu PCAP. Đếm
trước bộ lọc nếu cần tiếp tục quan sát nguồn đã bị chặn. Gói phân mảnh, gói
không đủ IPv4 Total Length bị bỏ và đếm riêng. ARP vẫn phải đi qua bridge,
nhưng không đưa vào sáu đặc trưng IPv4. Chính sách CRC/overflow và vị trí
đếm của phần cứng phải được kiểm, không mặc nhiên coi giống Python.

| Thứ tự | Raw | Công thức |
| --- | --- | --- |
| 0 | packet_count | Số gói IPv4 hợp lệ tới đích được chọn |
| 1 | mean_ip_bytes | floor(tổng IPv4 Total Length / số gói) |
| 2 | syn_ratio_q127 | floor(127 × số TCP SYN=1, ACK=0 / số gói IPv4) |
| 3 | src_count | Số IP nguồn phân biệt chính xác |
| 4 | dst_count | Số IP đích phân biệt chính xác; bằng 1 với đích /32 có gói |
| 5 | dst_port_count | Số cổng đích TCP/UDP phân biệt chính xác |

Không dùng độ dài Ethernet hoặc TCP payload thay IPv4 Total Length. Không
chỉ lấy số TCP làm mẫu số tỷ lệ SYN. SYN-ACK không phải SYN mở. Nếu `feat_core`
dùng bitmap/ước lượng cardinality thì cần đối chiếu và đánh giá lại theo đúng
phép đếm đó; không tự coi số bit bật là số địa chỉ/cổng phân biệt chính xác.

Model học từ các gói đã lọc theo nhãn. Việc lọc làm thay đổi thành phần lưu
lượng; khi thử lab trực tiếp, cần đối chiếu các cửa sổ có cả nền hợp lệ và
hoạt động tấn công, không mặc nhiên coi chúng giống cửa sổ PCAP đã lọc.

## Firmware và đóng gói

`ai_v5_prepare_window(packets, ip_bytes, syn_open, src, dst, ports, &feat)`
nhận **tổng byte IPv4** và **số SYN mở**, không nhận mean hay tỷ lệ đã tính.
Hàm tính mean, tỷ lệ, chia divisor rồi clip 0..127 đúng một lần.

`feat[7:0]=q0`, ... `feat[47:40]=q5`; ghi 32 bit thấp và 16 bit cao qua
driver thanh ghi thực tế của nhóm. Địa chỉ MMIO không được xác định trong
gói AI này. Nếu phần cứng đã xuất q thì không chia thêm lần nữa.

Chỉ skip cửa sổ **RAW packet_count=0**. Cửa sổ 1–7 gói vẫn hợp lệ dù q0=0.
Hàm guard trả 0 khi rỗng và ghi feat=0; CPU không phát start cho trường hợp
này. Hàng `empty_skip` trong vector không yêu cầu một class Normal giả.

## Cổng core

`clk`, `rst_n`, `start`, `feat[47:0]`, `busy`, `done`, `class_id[1:0]`,
`scores[47:0]`.

- Reset đồng bộ mức thấp; hủy phép tính đang chạy.
- Start là xung một clock, được nhận khi busy=0; feat được chốt tại cạnh đó.
- Start khi busy=1 bị bỏ qua. CPU phải giữ đúng giao dịch hoặc xếp hàng ngoài core.
- Done là xung một clock; busy về 0 khi done=1. Wrapper CPU cần chốt cờ done
  nếu CPU không đọc kịp xung; không polling trực tiếp một xung không được giữ.
- scores[15:0], [31:16], [47:32] là Normal/SYN/Scan, mỗi giá trị int16 **có dấu**.
- class_id=0 Normal, 1 SYN flood, 2 vertical scan; hòa điểm chọn lớp nhỏ hơn.
- Scores không phải xác suất. 84 chu kỳ đã đo trong mô phỏng; chưa suy ra
  timing trên bo hoặc độ trễ chặn Ethernet.

AI chỉ phân loại cửa sổ. Gói giao diện không bổ sung IP hay luật chặn.
CPU/bộ lọc của nhóm quy kết nguồn, quản lý whitelist/blacklist, điều kiện
xác nhận, timeout và TTL theo thiết kế thực tế. Khi nhiều nguồn cùng có
trong cửa sổ, `class_id` không tự cho biết nguồn nào cần bị chặn.

## Vector bàn giao

`INTEGRATION_V5.json`/CSV và `ai_v5_handoff_vectors.h` có tổng counter → raw
→ q → feat_lo/hi → ba scores → class. Đây là vector kiểm số học đã dựng,
không phải PCAP kiểm thử độc lập, không đưa chúng vào tập học. 36 hàng có
gói được cấp core; một hàng rỗng kiểm CPU không phát start.

Trình tự đối chiếu: kiểm raw trước, rồi q/feat, sau đó scores, cuối cùng
class. Nếu raw khác nhau, kiểm phạm vi đích, chiều, mốc cửa sổ và cách đếm
trước khi kết luận trọng số sai. Khi raw/q đã đúng mà scores khác, kiểm
phiên bản core/ROM, kiểu signed và handshake/đóng gói.
