# Đếm chính xác theo IP đích trước khi đọc PCAP capture17

Kết quả thực tế ở ba bản trích capture35:216.18.168.16 có763789 gói TCP,378 SYN mở và đỉnh3 SYN/giây trong406 cửa sổ đầy đủ;54.39.87.104 có4016458 TCP nhưng chỉ7 SYN mở;209.97.190.136 có6304727 TCP và0 SYN mở. Chưa chọn thêm dữ liệu SYN flood đã xác minh từ ba đích này. Không đổi các dòng đó thành Normal và không thay model.

Capture17 còn13655172 flow DDoS TCP có dấu S trong log, tổng27310841 orig_pkts theo metadata. Cần biết chúng tập trung vào một máy hay rải trên nhiều IP. Bảng ứng viên trước có giới hạn bộ nhớ và chưa xếp hạng đầy đủ theo số gói của từng flow; bước này đếm chính xác tất cả đích, kể cả đích chỉ có một flow nhưng nhiều orig_pkts.

## Chạy trên Ubuntu

Tải dem_dich17.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads thành dem_dich17. Chạy:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/dem_dich17/DEM_DICH17.py \
  --screen-output ~/iot23_sang_loc_01 \
  --output ~/iot23_dich17_01
```

Chỉ đọc file .log.gz capture17 đã lọc, không đọc archive/PCAP và không tải lại dữ liệu. Dùng NumPy đã có trong .venv. Cần khoảng250 MB trống cho tệp tạm; chương trình tự kiểm dung lượng. Không giữ hàng triệu IP dạng từ điển trong RAM: lưu bản ghi IPv4/orig_pkts12 byte trên đĩa, sắp xếp rồi cộng chính xác theo từng nhóm IP. Tệp tạm được xóa khi hoàn tất; log gốc không thay đổi.

Với13,6 triệu flow, quá trình có thể mất vài phút hoặc hơn tùy VM. Có tiến độ khi đọc/đếm; giai đoạn sắp xếp có thể im lặng một lúc. Đợi DONE hoặc ERROR. Đầu ra phải là thư mục mới; nếu chạy lại dùng ~/iot23_dich17_02, không xóa dữ liệu nguồn.

Khi DONE, gửi kết quả:

```bash
cat ~/iot23_dich17_01/TOM_TAT_DICH.csv
```

Mở bảng chi tiết nếu cần:

```bash
firefox ~/iot23_dich17_01/MO_DICH.html
```

## Ý nghĩa và giới hạn

- distinct_dst_ips: số IP đích phân biệt trong toàn bộ flow ứng viên, đếm chính xác.
- max_flows_per_dst: số flow lớn nhất tại một IP.
- max_known_orig_pkts_sum_per_dst: tổng orig_pkts đã biết lớn nhất tại một IP, theo metadata của log.
- max_orig_pkts_in_one_flow: orig_pkts lớn nhất của một flow, giúp không bỏ qua flow lớn chỉ vì ít flow.
- missing_orig_pkts_rows: số dòng thiếu orig_pkts. Thiếu không được diễn giải là0 gói thật; bảng chỉ cộng các giá trị đã biết.

Các bảng chi tiết lấy hợp của20 đích nhiều flow nhất,20 đích nhiều tổng orig_pkts đã biết nhất và20 đích có flow lớn nhất. Cả thứ hạng và số đếm cho các đích được chọn được kiểm lại bằng một lượt đọc log độc lập. Báo cáo thống kê phân bố số flow/tổng orig_pkts theo từng IP trên toàn bộ ứng viên.

Đây vẫn là thống kê flow gốc. Không chuyển orig_pkts thành PPS bằng cách chia đều theo duration hoặc đổ hết vào giây bắt đầu. Không coi dấu S trong history là cờ thực tế của tất cả packet. Chưa xác minh SYN flood/vertical scan, chưa tạo sáu đặc trưng hoặc nhãn dự án; model giữ nguyên. Kết quả giúp quyết định có đích nào đáng kiểm PCAP tiếp theo hay không.
