# Sáu đặc trưng cố định của AI V6

Tên tệp được giữ để khớp chú thích trong header C. V6 dùng divisors cố định `[8,2,1,1,1,1]`, không tự học hoặc scale lại lúc suy luận.

Chỉ tính IPv4 ingress tới receiver được bảo vệ /32, theo cửa sổ một giây có cùng mốc thời gian. ARP và chiều ngược lại không cộng vào thống kê này. Bỏ IPv4 phân mảnh và gói không đủ IP Total Length. Đếm IP/cổng phân biệt chính xác; có thể bão hòa sau khi đạt 128 vì q bão hòa ở 127. Không thay bằng bitmap/hash ước lượng chưa đối chiếu.

| i | raw[i] | Công thức |
|---|---|---|
| 0 | packet_count | Số gói IPv4 hợp lệ |
| 1 | mean_ip_bytes | floor(tổng IPv4 Total Length / N), không dùng độ dài Ethernet |
| 2 | syn_ratio_q127 | floor(127 × số SYN mở / N) |
| 3 | src_count | Số IP nguồn phân biệt |
| 4 | dst_count | Số IP đích phân biệt (1 với receiver /32) |
| 5 | dst_port_count | Số cổng đích TCP/UDP phân biệt, không tạo cổng giả cho ICMP |

SYN mở dùng điều kiện `(tcp_flags & 0x12) == 0x02`; SYN-ACK không tính. Mẫu số là toàn bộ IPv4 hợp lệ trong hướng thống kê. Chốt thống kê trước bộ lọc để vẫn quan sát nguồn đã chặn.

`q[i] = min(127, raw[i] // divisor[i])`; mỗi q là số nguyên không âm từ 0 đến 127. Gói 48 bit có q0 ở bit 7:0 và q5 ở bit 47:40. Không đưa IP dưới dạng số, nhãn, timestamp hoặc session ID vào sáu đầu vào.

N = 0: không gọi suy luận, không coi kết quả cũ là Normal. N từ 1 đến 7 vẫn gọi suy luận dù q0 = 0. Mốc/reset cửa sổ phần cứng cần được đối chiếu khi so với PCAP; phần mềm dùng floor(timestamp / một giây), còn reset bo tùy ý có thể tạo cửa sổ khác.

Hàm C nhận **tổng byte IPv4 và số gói SYN thực**, không nhận mean/percent đã làm tròn từ UART. Điều kiện đầu vào: counter không âm, SYN ≤ N, N/SYN/cardinality vừa uint32 và tổng byte vừa uint64. Người phụ trách trích đếm phần cứng cung cấp các counter theo chuẩn này.
