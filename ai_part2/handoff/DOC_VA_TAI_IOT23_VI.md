# Tải IoT-23 để đọc và hiểu dữ liệu

Nguồn chính thức: Stratosphere Laboratory / CTU, https://www.stratosphereips.org/datasets-iot23 . Các tệp gốc được tải trực tiếp bằng HTTPS từ máy chủ công bố https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/ .

## 1. Bắt đầu bằng năm capture nhỏ

Gói hỗ trợ `iot23_de_doc.zip` chứa chương trình tải và hướng dẫn. Khi chạy, chương trình lấy năm log gốc và một PCAP bình thường, khoảng **28 MB tải về**, sau đó tạo CSV và trang đọc offline. Không cần cài thêm thư viện Python, không huấn luyện hoặc thay model hiện tại. Đây là **một phần IoT-23 để học cách đọc**, không phải toàn bộ 23 capture.

Tải ZIP từ gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads thành `iot23_de_doc`, rồi mở Terminal Ubuntu:

```bash
cd ~/Downloads/iot23_de_doc
python3 tai_iot23.py --output dataset
firefox dataset/MO_DE_DOC.html
```

Chờ dòng DONE trước khi mở. Python 3.8 trở lên được hỗ trợ; Ubuntu hiện tại có Python phù hợp. Nếu tạm gián đoạn, chạy lại cùng lệnh: các tệp tải xong có đúng hash được giữ lại, tệp chưa hoàn tất được tải lại. Chương trình không tiếp tục giữa chừng trong từng tệp nhỏ; lệnh wget -c ở phần tải bộ lớn bên dưới có khả năng tiếp tục tải tệp lớn.

| Capture | Tệp log gốc | Số dòng luồng đã kiểm tra |
|---|---|---:|
| CTU-Honeypot-Capture-4-1, Philips Hue | conn.log.labeled | 452 |
| CTU-Honeypot-Capture-5-1, Amazon Echo | conn.log.labeled | 1374 |
| CTU-IoT-Malware-Capture-34-1 | conn.log.labeled | 23145 |
| CTU-IoT-Malware-Capture-44-1 | conn.log.labeled | 237 |
| CTU-IoT-Malware-Capture-3-1 | conn.log.labeled | 156103 |
| Tổng năm log | | 181311 |

Phần PCAP là toàn bộ capture gốc Philips Hue4: 4.594.492 byte sau giải nén. Bản xz tải về chỉ 376.840 byte. Các capture mang tên Malware vẫn có thể chứa cả flow Benign theo nhãn nguồn; không gán mọi dòng trong một capture thành tấn công.

## 2. Sau khi tải, đọc tệp nào?

```text
dataset/
├── MO_DE_DOC.html             <- mở đầu tiên bằng Firefox/Edge/Chrome
├── DOWNLOAD_MANIFEST.json     <- URL nguồn, hash, dung lượng, số dòng
├── csv/
│   ├── CTU-Honeypot-Capture-4-1.csv  <- bắt đầu đọc bảng nhỏ này
│   └── ...                   <- đủ các dòng của từng log đã tải
└── raw/
    ├── CTU-Honeypot-Capture-4-1/
    │   ├── bro/conn.log.labeled
    │   ├── 2018-10-25-14-06-32-192.168.1.132.pcap.xz
    │   └── 2018-10-25-14-06-32-192.168.1.132.pcap
    └── ...
```

Trang HTML có giải thích cột, bảng xem trước và lọc theo capture/nhãn/tìm IP. Bảng xem trước lấy tối đa 20 dòng cho mỗi cặp nhãn trong từng capture để dễ đọc; không dùng phần xem trước để suy ra phân bố nhãn. CSV chứa tất cả các dòng của log tương ứng. Có thể mở CSV trong LibreOffice Calc, Excel hoặc VS Code. PCAP mở bằng Wireshark nếu muốn xem từng gói; không cần Wireshark để đọc trang HTML và CSV.

Các log gốc được giữ nguyên byte. CSV chỉ chuẩn hóa tên `det_label` hoặc `detailed-label` thành `detailed_label`; giữ nguyên giá trị nhãn và các trường còn lại, kể cả dấu `-` và chữ hoa/thường.

## 3. Một dòng dữ liệu thật dễ hiểu

Dòng đầu trong log Philips Hue có những trường sau (đây là một số cột được chọn để minh họa):

```csv
id.orig_h,id.orig_p,id.resp_h,id.resp_p,proto,duration,orig_pkts,resp_pkts,label,detailed_label
192.168.1.132,58687,216.239.35.4,123,udp,0.114184,1,1,benign,-
```

Nghĩa là phía khởi tạo 192.168.1.132:58687 liên lạc với 216.239.35.4:123 bằng UDP; luồng dài khoảng 0,114 giây; ghi một gói mỗi chiều; nhãn gốc benign. Cổng UDP123 thường dùng cho đồng bộ thời gian NTP. IoT-23 có DNS/NTP/HTTPS và nhiều loại lưu lượng khác, không chỉ MQTT như lab của chúng ta.

| Cột | Cách hiểu |
|---|---|
| ts | Timestamp bắt đầu luồng, theo Unix time |
| uid | Mã định danh luồng của Zeek |
| id.orig_h / id.orig_p | IP / port phía khởi tạo luồng |
| id.resp_h / id.resp_p | IP / port phía còn lại |
| proto | Giao thức tcp, udp... |
| duration | Thời lượng cả luồng, tính bằng giây |
| orig_pkts / resp_pkts | Số gói hai chiều của cả luồng |
| label | Nhãn tổng quát gốc như Benign/benign/Malicious |
| detailed_label | Nhãn chi tiết gốc như DDoS, C&C, PartOfAHorizontalPortScan... |

Không mặc định phía orig là kẻ tấn công. `-` biểu thị giá trị không được ghi ở trường đó, không mặc định là số 0. `conn_state=S0` tự nó không chứng minh tấn công; có thể xuất hiện trong đối chứng bình thường.

## 4. Khác dữ liệu huấn luyện sáu đặc trưng thế nào?

- Một dòng **PCAP** là một gói/frame đã bắt.
- Một dòng **conn.log.labeled/CSV ở đây** là một luồng do Zeek tóm tắt; có thể kéo dài nhiều giây.
- Một dòng **CSV đưa vào model v3** là sáu đặc trưng của cửa sổ một giây theo đúng hướng IPv4 ingress.

Không coi một flow là một cửa sổ một giây, không dùng trường history của Zeek để suy ra tỷ lệ SYN mỗi giây chính xác. Muốn tạo sáu đặc trưng giống v3 cần đọc PCAP với đúng contract. Nhãn DDoS không tự động là SYN flood; PartOfAHorizontalPortScan là quét ngang, không phải vertical scan. Bộ tải này giữ nhãn gốc, không đổi chúng sang 0/1/2 của model.

## 5. Nếu muốn tải toàn bộ IoT-23

Trang chính thức liệt kê hai bản. Máy chủ được kiểm tra ngày 02/11/2026 trả các dung lượng tệp nén sau; GB ở bảng tính theo 1 GB = 1.000.000.000 byte:

| Bản | Nội dung theo trang công bố | Tệp nén |
|---|---|---:|
| Full | Có PCAP, README và log của các capture | 21.510.801.277 byte, khoảng 21,5 GB |
| Small | Chỉ README và log, không có PCAP | 9.373.916.249 byte, khoảng 9,4 GB |

Full: https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_full.tar.gz

Small: https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_small.tar.gz

Đây là các link nguồn chính thức, không nằm trong gói năm capture nhỏ. Chỉ đọc bảng log thì Small phù hợp; muốn tự trích sáu đặc trưng từ mọi capture cần PCAP của bản Full hoặc tải PCAP từng capture. Dung lượng giải nén lớn hơn tệp tải về; kiểm tra dung lượng ổ ảo trước khi chọn tải toàn bộ.

Ví dụ tải bản chỉ log bằng wget, có tiếp tục khi mạng gián đoạn:

```bash
mkdir -p ~/Downloads/IoT23_day_du
cd ~/Downloads/IoT23_day_du
wget -c https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_small.tar.gz
```

Nguồn mô tả và thông tin trích dẫn: https://www.stratosphereips.org/datasets-iot23 . Mã kiểm hash trong gói hỗ trợ dùng SHA256 ghi nhận từ các bản nguồn đã kiểm tra; không gọi mọi hash đó là checksum do nhà công bố cung cấp.
