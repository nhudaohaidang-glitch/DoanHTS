# Sàng lọc toàn bộ nguồn IoT-23 trước khi chọn thêm dữ liệu

Danh sách người dùng gửi có84 tệp:39 PCAP,23 log nhãn và22 tệp ghi chú, thuộc20 kịch bản malware và3 kịch bản honeypot bình thường. PCAP chiếm66510461999 byte; log nhãn47060783463 byte; tổng113571284237 byte. Một số PCAP là bản trích của cùng bản gốc, không phải39 nguồn độc lập để chia train/test.

Bộ2901 dòng trước đây chỉ tái lập Hue4 và đoạn SYN đã kiểm của capture34; không phải kết quả sàng lọc mọi kịch bản trong archive.

Cột selected=True/False trong KIEM_KE.csv chỉ ghi tệp có được công cụ cũ chọn hay không, không phải nhãn Normal/tấn công. Công cụ sàng lọc mới đọc cả23 log, không chỉ các dòng selected=True.

## Công cụ này làm gì

Đọc lại archive theo luồng một lần, kiểm đúng các log đã liệt kê trong KIEM_KE.csv. Thống kê mọi nhãn gốc của từng log. Giữ các dòng DDoS dùng TCP trong DDoS_TCP_CAN_KIEM_TRA dưới dạng .log.gz, giữ nguyên header/nhãn gốc. Chúng là ứng viên phải kiểm tiếp bằng PCAP, chưa được đổi thành SYN flood.

Chỉ giữ log Benign của các kịch bản Honeypot riêng trong NORMAL_LOG_GOC. Không tự gán Normal cho một cửa sổ lẫn lưu lượng malware chỉ vì một flow được gắn Benign. Somfy vẫn thuộc nhóm test đã dành riêng cho v3, không tự đưa vào train.

Không lưu toàn bộ PCAP/log ra ổ Ubuntu. Không xuất các flow UDP DDoS làm mẫu SYN. Không đổi HorizontalPortScan thành vertical scan. Vẫn thống kê các nhãn không được xuất trong BAO_CAO_LOC.json. Không tạo nhãn ba lớp hoặc thay model.

Một dòng log là một flow có thể kéo dài nhiều giây. Đây chưa phải bảng sáu đặc trưng. Bước sau mới chọn PCAP/đích/thời gian, kiểm cờ gói/hành vi, rồi tính sáu đặc trưng từ đủ lưu lượng vào cửa sổ một giây và xem nhãn có rõ ràng hay không. Chưa xác minh vertical scan không đồng nghĩa toàn bộ PCAP không có hành vi đó.

## Cách chạy trong Ubuntu

Giữ archive gốc trên Windows, các thư mục iot23_work_01 và iot23_khoi_phuc_01. Tải loc_nhan_iot23.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads thành loc_nhan_iot23.

```bash
~/ai_part2/.venv/bin/python ~/Downloads/loc_nhan_iot23/LOC_NHAN.py \
  --archive /media/sf_Downloads/iot_23_datasets_full.tar.gz \
  --inventory ~/iot23_work_01/KIEM_KE.csv \
  --output ~/iot23_sang_loc_01
```

Cần ít nhất1 GiB trống. Tổng log xuất được giới hạn1 GiB ở dạng nén. Chương trình kiểm dung lượng trong lúc chạy; nếu vượt hạn mức sẽ báo ERROR và status=failed, không báo hoàn tất giả hoặc lặng lẽ cắt bớt dữ liệu.

Đây là một lượt sàng lọc mới trên tất cả23 log, không phải chạy lại dự đoán2901 dòng. Do tar.gz đọc tuần tự, phải đọc qua archive21 GB và giải nén luồng, dù không ghi hết ra đĩa. Sàng lọc hàng trăm triệu flow có thể mất nhiều chục phút hoặc hơn trên VM; có tiến độ khoảng10 giây/lần. Không tải lại dataset từ Internet. Nên để Terminal chạy đến DONE hoặc ERROR.

Khi hiện DONE:

```bash
firefox ~/iot23_sang_loc_01/MO_KET_QUA_LOC.html
```

Sau đó gửi BAO_CAO_LOC.json hoặc TONG_HOP.csv. Chưa cần gửi file .log.gz lớn hay PCAP. Chưa train trực tiếp bằng các file ứng viên. Nếu lỗi, gửi thông báo và giữ thư mục kết quả; khi phải chạy lại dùng tên đầu ra mới, không xóa dữ liệu gốc.

## Căn cứ chọn nguồn

Bảng nhãn công bố có DDoS ở capture34,43,44,60,17,35 và7. Không có nhãn vertical scan riêng trong bảng này; nhiều dòng được gắn PartOfAHorizontalPortScan. Điều này không chứng minh không có vertical scan trong các gói, nhưng không cho phép đổi thẳng nhãn.

Đã đọc đầy đủ log công bố của capture7,1581263847 byte, SHA2563d603dc7c5a78f59b65aee892c8ccdca6023c8517ce1322eda6ecf2d903bfd73:11454714 flow,39584 flow DDoS đều UDP từ192.168.100.108 đến64.237.233.111:80. Vì vậy không lấy các flow đó làm SYN. Log trong archive người dùng vẫn được kiểm/thống kê riêng khi chạy công cụ, không giả định chỉ vì cùng tên/dung lượng là cùng nội dung.

Các preview có giới hạn ở capture17 và60 chỉ là thăm dò, không phải kiểm tra toàn capture: capture17 có flow DDoS TCP đến nhiều IP khác nhau; capture60 có dòng DDoS TCP history=C/conn_state=OTH. Các ví dụ này chưa đủ để gán SYN flood; cần PCAP. Không gắn nhãn tự động theo model dự đoán.

Nguồn nhãn chính thức: https://www.stratosphereips.org/datasets-iot23 . Các nguồn ghi nhận trước đây và giới hạn xem reports/IOT23_FIXED_SCOPE_FINDINGS.md. Model v3, sáu đặc trưng, định nghĩa SYN/vertical và dữ liệu lab hiện tại được giữ nguyên.
