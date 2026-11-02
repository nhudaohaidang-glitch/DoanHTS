# Chọn tiếp nguồn SYN từ các log đã lọc

Kết quả người dùng gửi đã sàng lọc23 log với325309946 flow gốc. DDoS dùng TCP còn4 capture:17 có13655172 flow;34 có14393;35 có2185297;60 có3578431, tổng19433293. Đây là flow, không phải số gói hoặc số mẫu cửa sổ một giây. Capture43 có65803 DDoS UDP và0 DDoS TCP, không dùng các flow đó làm SYN.

Không chạy lại archive21 GB ở bước này. Đọc các file .log.gz đã lưu trong ~/iot23_sang_loc_01, kiểm checksum theo báo cáo cũ và phân tích bằng chứng trong log để chọn đích/thời gian cần kiểm PCAP tiếp.

## Chạy trên Ubuntu

Tải chon_nguon_iot23.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads, để có ~/Downloads/chon_nguon_iot23/CHON_NGUON.py.

```bash
~/ai_part2/.venv/bin/python ~/Downloads/chon_nguon_iot23/CHON_NGUON.py \
  --screen-output ~/iot23_sang_loc_01 \
  --output ~/iot23_nguon_syn_01
```

Chỉ dùng thư viện Python chuẩn, không cài thêm, không đọc PCAP/archive, không tải Internet. Đọc mỗi log ứng viên hai lượt để giữ ít IP đích trong RAM rồi đếm lại chính xác các đích đó. Với khoảng19,4 triệu flow có thể mất vài phút hoặc hơn tùy VM; có tiến độ khoảng10 giây/lần. Không ghi đè thư mục cũ. Nếu phải chạy lại dùng đầu ra mới, chẳng hạn ~/iot23_nguon_syn_02.

Khi hiện DONE:

```bash
firefox ~/iot23_nguon_syn_01/MO_NGUON_SYN.html
```

Sau đó gửi phần tóm tắt ngắn bằng lệnh:

```bash
cat ~/iot23_nguon_syn_01/TOM_TAT_TCP.csv
```

Nếu ERROR, gửi nguyên thông báo; không mở kết quả như một phân tích hoàn tất khi status=failed. Không xóa log cũ, sửa nhãn hay thay model.

## Ý nghĩa các số

- history_S_flows: số flow có ký hiệu S viết hoa trong Zeek history, tức log ghi nhận SYN theo hướng khởi tạo. Chưa xác nhận cờ của mọi gói, tốc độ hoặc SYN flood; một kết nối hợp lệ cũng có SYN.
- history_C_flows: số flow có C viết hoa, log ghi bằng chứng checksum lỗi theo hướng khởi tạo. Không đổi chúng thành SYN flood và không dùng thiếu bằng chứng trong log để kết luận không có gói thật.
- orig_pkts_metadata_sum: tổng orig_pkts theo log, không phải số gói mới được giải mã từ PCAP. Dòng có orig_pkts thiếu được đếm riêng trong JSON.
- Các IP đích: đếm lại chính xác số flow của đích được giữ, số flow mang S/C, các cổng, thời gian và metadata. Số cổng tính trên cả log, chưa phải trong một giây. Không lấy các con số này làm sáu đầu vào FPGA.

Ví dụ đã đối chiếu trước đây: capture34 có133 flow mang S tới71.61.66.148:80, tổng40568 orig_pkts theo log; PCAP độc lập xác nhận40568 gói SYN và21 cửa sổ đầy đủ một giây.14260 flow DDoS TCP khác trong cùng capture mang C, không phải được gán SYN tự động chỉ vì native label=DDoS.

Để bộ nhớ không tăng theo hàng triệu IP của scan ngang, dùng hai bộ Misra-Gries, mỗi bộ tối đa65536 đích: một cho tất cả flow ứng viên, một cho flow có S. Lượt thứ hai đếm lại các đích đã giữ. Trang hiển thị tối đa20 đích, kết hợp đích nhiều S và đích nhiều flow tổng. Báo cáo ghi giới hạn trên về số flow của mỗi đích không hiển thị, gồm cả đích bị lược và đích đã đếm nhưng không nằm trong20 dòng. Không coi việc không xuất hiện trong bảng là không có tấn công; cũng không gọi bảng là top20 toàn cục khi chưa có bằng chứng đó.

Đầu ra BAO_CAO_NGUON.json và DICH_CAN_KIEM_TRA.csv giúp chọn PCAP/đích/thời gian để kiểm tra tiếp. Chưa gán nhãn SYN flood hoặc vertical scan, chưa tạo tập train, chưa đánh giá model trên dữ liệu mới. Vertical scan chưa được kiểm tra bằng công cụ này; các nhãn HorizontalPortScan vẫn không được đổi tên. Model v3 và các báo cáo đánh giá cũ giữ nguyên.
