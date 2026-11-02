# Trích PCAP capture35 và kiểm SYN theo gói thực tế

Kết quả log người dùng đã gửi:

| IP đích | Flow DDoS TCP | Flow có S | orig_pkts theo log | Cổng đích trên cả log |
|---|---:|---:|---:|---:|
|216.18.168.16|268404|259|763789|2|
|54.39.87.104|1008350|6|4016458|1|
|209.97.190.136|908543|0|6304672|2|

Chọn216.18.168.16 làm đích phân tích sáu đặc trưng trước. Chưa suy ra số cửa sổ SYN từ259 flow. Hai cổng trên cả log chưa chứng minh vertical scan.

## Công cụ thực hiện

Đọc archive theo luồng đến khi lấy đủ PCAP chính của capture35 và log nhãn gốc cùng capture. Lưu bản trích theo cả ba IP trên, giữ nguyên byte của global header, record header và gói; không chỉ giữ gói SYN. Các bản trích khác được lưu để có thể kiểm tiếp mà không đọc lại archive.

Chỉ giữ log TCP theo các IP đích nhưng giữ mọi nhãn gốc trong phần đó, gồm Benign/C&C/nhãn khác nếu có. Kiểm SHA256 toàn bộ log gốc khớp báo cáo sàng lọc trước, không chỉ kiểm file DDoS ứng viên. Khi đối chiếu packet, một tuple/thời gian có nhãn xung đột sẽ không được chấp nhận là DDoS duy nhất.

Sau khi đọc đủ hai thành viên, dừng đọc archive. Tiến độ archive vì vậy có thể kết thúc trước100%. Không tải Internet, không lưu PCAP gốc3,81 GB hay bung toàn bộ113 GB. Không tính lại hash toàn archive ở lượt này: báo cáo ghi rõ hash archive là ghi nhận của lượt sàng lọc trước; hash PCAP gốc và log gốc được tính đầy đủ tại lượt mới.

## Chạy trên Ubuntu

Giữ các thư mục kết quả cũ và archive gốc. Tải trich_pcap35.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw, giải nén trong Downloads thành trich_pcap35.

```bash
~/ai_part2/.venv/bin/python ~/Downloads/trich_pcap35/TRICH_PCAP35.py \
  --archive /media/sf_Downloads/iot_23_datasets_full.tar.gz \
  --screen-output ~/iot23_sang_loc_01 \
  --profile-output ~/iot23_nguon_syn_01 \
  --output ~/iot23_pcap35_01
```

Cần ít nhất2,25 GiB trống. Tổng cache PCAP được giới hạn2 GiB; nếu vượt sẽ báo ERROR thay vì lặng lẽ cắt dữ liệu. Chương trình không ghi đè thư mục đầu ra đã có. Khi phải chạy lại dùng tên mới như ~/iot23_pcap35_02.

Đây là lượt đọc PCAP thật, khác các bước chỉ đọc log vừa rồi. Nó cần đọc phần đầu archive để đến capture35, sau đó đọc hết PCAP và log của nguồn này. Có thể mất nhiều phút hoặc lâu hơn trên VM. Giai đoạn trích có tiến độ; bước tính sáu đặc trưng bằng Scapy có thể im lặng vài phút, không đóng Terminal khi chưa DONE/ERROR.

Khi hiện DONE:

```bash
firefox ~/iot23_pcap35_01/MO_KET_QUA_PCAP.html
```

Gửi bảng ngắn:

```bash
cat ~/iot23_pcap35_01/TOM_TAT_PCAP.csv
```

Nếu ERROR, gửi nguyên thông báo và giữ thư mục chẩn đoán; không dùng kết quả có status=failed để train.

## Cửa sổ nào được chọn làm SYN

Sáu đặc trưng dùng nguyên part2/features.py, ingress IPv4 tới216.18.168.16, cửa sổ một giây theo timestamp từng gói; loại fragment/truncated đúng contract hiện tại. Tỷ lệ SYN tính SYN=1/ACK=0 trên tất cả gói IPv4 hợp lệ, không tính một gói có cả SYN và ACK là SYN mở. Divisor vẫn [8,2,1,1,1,1]. Không bỏ dòng chỉ vì q0=0.

Đối chiếu các gói TCP với log gốc theo tuple hướng khởi tạo và khoảng thời gian, dung sai1 ms. Sắp thời gian các gói SYN mở khớp duy nhất Malicious/DDoS; ngắt episode khi khoảng cách giữa hai gói lớn hơn2 giây. Quy tắc phân đoạn này được đặt trước khi xem kết quả capture35, không dựa vào model dự đoán.

Chỉ cửa sổ đầy đủ nằm trong cả capture và episode, có gói, với toàn bộ gói IPv4 hợp lệ đều là SYN mở và đều khớp nhãn Malicious/DDoS duy nhất, mới được đưa vào syn_da_kiem_tra và gán nhãn1 riêng. Không tự gán nhãn Normal cho phần còn lại. Những cửa sổ trộn SYN với ACK/UDP/lưu lượng khác hoặc có packet không khớp/nhãn xung đột không được chọn làm cửa sổ SYN thuần.

Đây là bằng chứng gói và nhãn native cho các cửa sổ SYN thuộc đợt DDoS. Báo cáo còn ghi tốc độ gói/giây để đánh giá hành vi; không coi một SYN riêng lẻ bất kỳ là flood. Chưa huấn luyện hay đánh giá model trên các dòng mới. training_ready=false vì đây chỉ là phần một lớp, còn cần xem chất lượng, độ đa dạng và cách chia nguồn.

Nếu không có cửa sổ đủ điều kiện, công cụ vẫn báo số0 đúng thực tế và không tạo bộ nhãn giả. Các bản trích PCAP/bằng chứng vẫn giữ lại để kiểm tiếp.

## Đầu ra

- pcap_da_loc/: PCAP theo ba IP đích, byte gốc được giữ nguyên.
- nhan_goc_theo_dich/: log TCP theo đích, giữ mọi nhãn gốc liên quan.
- tat_ca_cua_so_dich/: sáu raw, sáu q và bằng chứng từng cửa sổ hợp lệ của đích chính; chưa gán nhãn cho mọi dòng.
- syn_da_kiem_tra/: nếu có, sáu raw, sáu q, y.csv chỉ có1 và nguồn/thời gian/episode riêng.
- BAO_CAO_PCAP.json: hash nguồn/cache, cờ TCP, packet khớp, episode và số cửa sổ.
- TOM_TAT_PCAP.csv: một dòng kết quả cần gửi để chọn bước tiếp.

Tất cả IP/episode trích từ capture35 vẫn là một nhóm capture khi chia train/validation/test. Không chia ngẫu nhiên các giây cạnh nhau hoặc dùng một IP từ capture35 train rồi gọi IP khác cùng capture là test độc lập. Giữ nguyên model v3 và báo cáo lab cũ. Lớp vertical scan chưa được xác minh ở bước này.
