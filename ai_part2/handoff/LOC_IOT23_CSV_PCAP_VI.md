# Xuất IoT-23 thành tệp bình thường và SYN flood: CSV + PCAP

Công cụ này **xuất dữ liệu đã lọc**, không chỉ thống kê nguồn. Nguồn có bình
thường thì xuất bình thường; có SYN flood đã kiểm chứng thì xuất SYN flood;
có cả hai thì xuất cả hai; không có dữ liệu phù hợp thì bỏ qua, không tạo tệp
rỗng. Không huấn luyện hoặc thay model.

## Chạy trên Ubuntu của bạn

Ổ Ubuntu của bạn còn 67 GB; dùng ổ này. Ổ Downloads của Windows còn 9,7 GB,
không dùng để chứa kết quả hoặc dữ liệu tạm. Không cần chép archive sang Ubuntu.

1. Tải [loc_iot23_csv_pcap.zip](https://github.com/nhudaohaidang-glitch/DoanHTS/blob/ai-part2-starter-20261029/loc_iot23_csv_pcap.zip), bấm **Download raw**.
2. Giải nén trong Downloads của Ubuntu để có
   `~/Downloads/loc_iot23_csv_pcap/LOC_CSV_PCAP.py`.
3. Chạy một lệnh:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/loc_iot23_csv_pcap/LOC_CSV_PCAP.py
```

Công cụ dùng các tệp đã có:

- `/media/sf_Downloads/iot_23_datasets_full.tar.gz`
- `~/iot23_sang_loc_01/BAO_CAO_LOC.json`
- `~/iot23_work_01/KIEM_KE.csv`

Nó đọc archive hai lượt: lượt đầu xuất CSV và lập chỉ mục nhãn; lượt sau lọc
gói tin sang PCAP. Không bung toàn bộ 113,57 GB dữ liệu ra ổ đĩa. Tuy vậy,
phải đọc khoảng 21,51 GB nén mỗi lượt, kiểm tra 23 log và 39 PCAP; công việc
có thể mất vài giờ tùy máy ảo. Dòng `Sorting ... native label intervals` có
thể đứng lâu trong lúc sắp xếp chỉ mục trên đĩa.

Giữ máy và VirtualBox chạy đến dòng `DONE`. Nếu bị ngắt, chạy lại **đúng lệnh
trên**: công cụ kiểm checksum và dùng lại các nguồn đã xong. Phần đang dở
được làm lại; không phải bắt đầu lại mọi nguồn. Giữ nguyên gói công cụ và
các đầu vào khi chạy tiếp. Tệp có đuôi `.part` chưa hoàn tất.

## Kết quả

```text
~/iot23_da_loc_01/
├── binh_thuong/
│   ├── csv/       # Mỗi tệp nguồn có dòng Benign gốc
│   └── pcap/      # Mỗi PCAP nguồn có gói bình thường đủ điều kiện
├── syn_flood/
│   ├── csv/       # Flow thuộc đoạn SYN flood đã kiểm chứng
│   └── pcap/      # Gói SYN của đoạn đã kiểm chứng
├── DANH_SACH_TEP.csv
├── BAO_CAO_XUAT.json
├── MO_DU_LIEU_DA_LOC.html
└── .tam/          # Chỉ mục nhãn để lọc gói và chạy tiếp
```

Mở kết quả:

```bash
xdg-open ~/iot23_da_loc_01/MO_DU_LIEU_DA_LOC.html
```

Các tệp `.csv.gz` là CSV nén; giữ tất cả cột flow gốc, thêm `loai_da_loc`.
Mỗi dòng là **một flow Zeek**, không phải một gói, không phải sáu đặc trưng
model mỗi giây. Đọc bằng Python: `gzip.open(path, 'rt')` rồi `csv.DictReader`.
Các tệp `.pcap.gz` là PCAP nén, Wireshark mở trực tiếp được. Sau khi giải nén,
header và từng gói được giữ nguyên byte từ tệp nguồn.

## Quy tắc lọc

**Bình thường:** lấy nhãn `Benign` gốc trong **mọi log**, bao gồm capture malware.
Trong PCAP của capture malware, chỉ giữ IPv4 TCP/UDP/ICMP khớp địa chỉ, cổng,
giao thức và khoảng thời gian của flow Benign, cả hai chiều, dung sai 1 ms.
Khoảng thời gian trùng với nhãn khác bị loại. Gói không khớp, IPv6, phân mảnh
hoặc lỗi không tự được gán bình thường; số bị loại nằm trong báo cáo. Vì vậy
CSV có thể chứa flow mà PCAP lọc không giữ được gói nào.

Với ba kịch bản bình thường chính thức `CTU-Honeypot-Capture-4-1`, `5-1`,
`7-1`, nếu log chỉ có Benign, giữ toàn bộ các PCAP của kịch bản đó, kể cả ARP
và IPv6. Các tệp phụ có thể trùng gói với tệp chính; giữ tên nguồn riêng và
không coi chúng là các tập mẫu độc lập.

**SYN flood:** hiện chỉ chọn đoạn đã kiểm chứng trong capture 34, từ
`192.168.1.195` tới `71.61.66.148:80`, khoảng 22 giây. Kiểm nội dung 133 flow
gốc, checksum PCAP gốc và đúng **40.568 gói SYN mở** trước khi công bố tệp.
Chữ hoa/thường nhãn Benign và các tên cột nhãn chi tiết của Zeek được hỗ trợ;
log khác định dạng khoảng trắng vẫn phải có cùng nội dung flow SYN đã duyệt.

Không đổi mọi `DDoS` hay mọi flow có lịch sử `S` thành SYN flood. Capture 35
với các cửa sổ một gói trước đây không được đưa vào thư mục SYN flood. Các
nguồn khác vẫn xuất phần Benign; chưa có đoạn SYN flood được duyệt không phải
là kết luận chúng hoàn toàn không có SYN flood.

Công cụ đối chiếu log với checksum và số dòng trong kết quả sàng lọc trước
đó; kiểm SHA256 toàn archive sau mỗi lượt. Chỉ dùng bộ kết quả khi báo cáo có
`status: complete`. Trong khi chạy, các tệp đã hoàn tất từng nguồn vẫn được
lưu để chạy tiếp. Dữ liệu gốc và các kết quả trước đây được giữ nguyên.
