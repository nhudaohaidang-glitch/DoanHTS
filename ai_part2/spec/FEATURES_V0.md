# Dự thảo hợp đồng đặc trưng v0 — gửi người 1 và 3 trước khi ghép

Đây là hợp đồng của bộ mã này, chưa khẳng định giống RTL của thành viên khác.

Phạm vi: chiều ngoài -> trong, IPv4 có đích trong --target_net của manifest; cửa sổ 1 giây tumbling. PCAP được đọc theo timestamp, chỉ lấy cửa sổ hoàn toàn nằm trong start/end của manifest. Các cửa sổ phần đầu/cuối không đủ thời gian bị loại. ARP và chiều trả về không tính vào đặc trưng, nhưng bridge phải chuyển tiếp chúng. IPv4 fragment và gói bị cắt ngắn được bỏ và đếm rõ trong metadata.

| Thứ tự | Tên | Công thức số nguyên |
|---|---|---|
| f0 | packet_count | Số gói IPv4 hợp lệ đầu vào |
| f1 | mean_ip_bytes | floor(sum(IPv4 Total Length)/packet_count), rỗng = 0 |
| f2 | syn_ratio_q127 | floor(127 * syn_open_count / packet_count), rỗng = 0 |
| f3 | src_count | Số IP nguồn khác nhau |
| f4 | dst_count | Số IP đích khác nhau |
| f5 | dst_port_count | Số cổng đích TCP/UDP khác nhau |

SYN mở kết nối: TCP SYN=1 và ACK=0. SYN-ACK không tính. Mẫu số f2 bao gồm mọi IPv4 hợp lệ trong hướng thống kê, không chỉ TCP.

Mặc định đếm IP/cổng phân biệt chính xác để làm tham chiếu. Tùy chọn --distinct bitmap256 mô phỏng bảng 256 bit với hash XOR các byte của giá trị rồi lấy 8 bit thấp, đếm số bit 1, không ước lượng cardinality. Nó có thể va chạm. Không tùy tiện dùng mode này cho dữ liệu nếu người 3 dùng hash/kích thước khác. Hệ thống phải đếm trước bộ lọc nếu muốn vẫn quan sát nguồn đang bị chặn; việc này cần xác nhận với người 3.

Gốc cửa sổ phần mềm mặc định là epoch (floor(timestamp / window)). Đối chiếu RTL chỉ có ý nghĩa khi cửa sổ RTL được căn cùng mốc; clock reset tùy ý sẽ cho cửa sổ khác. Khi ghép, phải chốt mốc/reset hoặc căn lại dữ liệu, không báo phần cứng sai chỉ vì lệch cửa sổ.

## Lượng tử hóa đầu vào

- Học divisor cho mỗi đặc trưng trên TRAIN, là lũy thừa 2, nhỏ nhất đủ đưa max train về <=127.
- q_i = clamp(floor(raw_i / divisor_i), 0, 127).
- Divisor và shift tương ứng nằm trong model.json. Firmware phải dùng chính chúng, không tự scale lại.
- feat[7:0]=q0 ... feat[47:40]=q5. Đây là int8 không âm 0..127, không dùng -128..-1.
- Không đưa label/IP số học/time/session id vào sáu đầu vào.

## Nhãn và split

0 bình thường, 1 SYN flood, 2 TCP vertical scan. Nhãn là nhãn kịch bản/cửa sổ có thời gian được kiểm soát, không phải nhãn mỗi gói trong cửa sổ. Phiên tấn công chứa MQTT bình thường vẫn là cửa sổ tấn công nếu hoạt động tấn công thực sự diễn ra. Kiểm tra source.log và PCAP; nếu nguồn thử nghiệm không chạy thì không dùng nhãn đó.

Các phiên khác nhau nằm trong train/val/test; không cắt cửa sổ ngẫu nhiên rồi chia. SHA256 trùng bị từ chối. Chạy tối thiểu nhiều phiên cho mỗi lớp và thay đổi tải MQTT, tốc độ tấn công, tốc độ quét trước khi tin kết quả. Các lệnh minh họa một phiên/lớp/split chỉ để bắt đầu, chưa chứng minh khái quát.

Thứ tự ghi PCAP không bắt buộc theo timestamp: mỗi gói cập nhật bucket floor(timestamp/window) của chính nó, không dùng vị trí trong file làm mốc. Bộ đọc ghi lại số lần timestamp lùi và mức lùi lớn nhất, không bỏ gói hoặc sửa PCAP chỉ để ép thứ tự tăng. Các đảo thứ tự qua biên cửa sổ cũng phải được phân đúng bucket; đã có kiểm thử so với bản sắp thứ tự và tổng đếm thủ công. Timestamp không hữu hạn vẫn bị từ chối.
