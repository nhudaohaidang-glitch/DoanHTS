# Dữ liệu vertical scan: PCAP và CSV đã tạo sẵn

Đã tìm và kiểm tra PCAP mẫu **synscan.pcapng** trong kho công khai
[Chris Sanders / Packets](https://github.com/chrissanders/packets).
README của tác giả cho phép sử dụng với điều kiện trích nguồn; bản README
gốc được giữ cùng dữ liệu. Nguồn này nằm ngoài IoT-23.

## Dùng ngay

1. Tải [vertical_scan_pcap_csv.zip](https://github.com/nhudaohaidang-glitch/DoanHTS/blob/ai-part2-starter-20261029/vertical_scan_pcap_csv.zip), bấm **Download raw**.
2. Giải nén trong Downloads của Ubuntu, thành `vertical_scan_pcap_csv`.
3. Dữ liệu đã có sẵn trong `vertical_scan/pcap/` và `vertical_scan/csv/`.
   Có thể mở tệp `.pcap` bằng Wireshark, tệp `.csv` bằng LibreOffice hoặc Python.

Để thêm cạnh hai nhóm bình thường/SYN flood đã lọc, chạy:

```bash
python3 ~/Downloads/vertical_scan_pcap_csv/THEM_VERTICAL_SCAN.py
```

Lệnh này kiểm checksum rồi chép vào `~/iot23_da_loc_01/vertical_scan/`.
Các thư mục bình thường, SYN flood và báo cáo lọc IoT-23 được giữ nguyên.
Nếu thư mục vertical_scan đã tồn tại nhưng khác checksum, công cụ dừng và
giữ các tệp đó. Không cần đọc lại archive hoặc cài thêm thư viện cho lệnh chép.

```bash
xdg-open ~/iot23_da_loc_01/MO_BA_LOAI_DU_LIEU.html
```

## Có gì trong gói

```text
vertical_scan_pcap_csv/
├── THEM_VERTICAL_SCAN.py
├── HUONG_DAN.md
├── FILE_SHA256.json
└── vertical_scan/
    ├── pcap/chris_sanders_synscan_vertical.pcap
    ├── csv/chris_sanders_synscan_vertical.csv
    ├── nguon_goc/synscan.pcapng
    ├── nguon_goc/README_CHRIS_SANDERS.md
    ├── BAO_CAO_VERTICAL_SCAN.json
    └── MO_DU_LIEU_SCAN.html
```

## Bằng chứng là vertical scan

- Một IP nguồn: **172.16.0.8**.
- Một IP đích: **64.13.134.52**.
- **1.000 cổng đích phân biệt** bị thăm dò.
- **1.994 gói SYN mở** từ nguồn, **17 gói phản hồi**, tổng **2.011 gói**.
- **1.994 flow TCP theo 5-tuple**. Một cổng có thể có nhiều flow do thay đổi
  cổng nguồn khi thăm dò lại; số flow không phải số cổng.
- SYN thăm dò diễn ra khoảng **5,14 giây**. Toàn capture khoảng **23,09 giây**
  vì còn phản hồi muộn; báo cáo ghi riêng thời gian quét.

Đã kiểm tra hành vi một nguồn → nhiều cổng → cùng một IP đích. Không chọn
capture chỉ vì tên có chữ scan hoặc vì gói có cờ SYN. Một mẫu Nmap khác từ
Zeek được khảo sát nhưng không chọn: có nhiều IP đích và chỉ 1–2 cổng trên
mỗi đích, không phù hợp bằng mẫu này.

## Định dạng và nhãn

Nguồn chỉ phát hành PCAPNG, không kèm CSV nhãn. PCAP đã xuất là định dạng
Ethernet PCAP thông dụng; mỗi frame, thứ tự, độ dài và timestamp microsecond
được giữ nguyên. Header của container PCAPNG và PCAP khác nhau.

CSV được tính từ gói tin, mỗi dòng gom một TCP 5-tuple trong capture này.
`id.orig_h` luôn là máy quét; `id.resp_h` là đích. Cột `orig_pkts`, `resp_pkts`
và tổng byte IPv4 được tính riêng hai chiều. Các cột cờ TCP ghi dạng
`02:1` (cờ hex 02 xuất hiện một lần). `flow_id` do công cụ tạo.

`loai_da_loc=vertical_scan` và `label_basis=project_reviewed_packet_behavior`
là nhãn của dự án sau kiểm tra hành vi. Không phải nhãn Zeek hoặc nhãn CSV
gốc của nhà cung cấp. `project_class_id=2` trong báo cáo tương ứng quy ước
AI của nhóm, không phải một đầu vào trong sáu đặc trưng.

CSV này là bảng flow, chưa phải X_6_raw/X_6_fpga. Khi tạo đặc trưng hoặc
đối chiếu RTL, dùng đúng chiều ingress, mốc cửa sổ một giây và khoảng thời
gian đang quét; không gán mọi giây chỉ có phản hồi muộn thành scan đang hoạt động.

Đây là **một lần quét mẫu có sẵn**, không phải một bộ train/test nhiều phiên
độc lập, không chứng minh khả năng khái quát. Bộ mẫu không thay model và
không tự tạo thêm gói tin. Các IP/MAC và timestamp lịch sử được giữ nguyên;
khi dùng trong hệ thống thử nghiệm, cấu hình đường mạng phải phù hợp.

## Tái lập và nguồn

Commit nguồn: `0412fb1dc0aa671128f9da6689e0dbd4459c0b51`.

[PCAPNG tại commit đã chốt](https://github.com/chrissanders/packets/blob/0412fb1dc0aa671128f9da6689e0dbd4459c0b51/synscan.pcapng).
SHA256 PCAPNG: `3ef7a9011bcc2901080d3800d52fd5bb5cbcc1aeb8b5943bed3810868400aa58`.

Mã tạo trong repo: `ai_part2/tools/prepare_public_vertical_scan.py`.
Đọc PCAPNG đã giữ trong gói, kiểm hash, xác minh số gói/cổng và xuất lại
PCAP + CSV. Chỉ việc tái tạo dữ liệu mới cần Scapy; dữ liệu trong ZIP đã sẵn sàng.
