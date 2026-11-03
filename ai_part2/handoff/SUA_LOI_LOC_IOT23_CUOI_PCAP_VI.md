# Chạy tiếp sau lỗi PCAP capture 39

Lỗi bản cũ: `ERROR: Truncated, empty or changed source PCAP` ở cuối
`CTU-IoT-Malware-Capture-39-1/2019-01-09-21-25-11-192.168.1.194.pcap`.

Đã kiểm tra riêng 1 MiB đầu và 1 MiB cuối tệp PCAP do nhà cung cấp công bố.
Tệp có đúng 5.617.836.032 byte như bản kiểm kê của bạn. Gói cuối khai báo
60 byte, nhưng chỉ còn 32 byte dữ liệu: **thiếu 28 byte**. Chuỗi 13.796 bản
ghi hoàn chỉnh liên tiếp trong phần đuôi dẫn đến đúng bản ghi thiếu đó.
Đây là vấn đề ở phần đuôi PCAP gốc được công bố; không cần tải lại archive
21,51 GB để xử lý trường hợp này.

## Chạy tiếp

1. Tải [sua_loi_loc_iot23.zip](https://github.com/nhudaohaidang-glitch/DoanHTS/blob/ai-part2-starter-20261029/sua_loi_loc_iot23.zip), bấm **Download raw**.
2. Giải nén trong Downloads của Ubuntu để có
   `~/Downloads/sua_loi_loc_iot23/LOC_TIEP.py`.
3. Chạy:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/sua_loi_loc_iot23/LOC_TIEP.py
```

Giữ nguyên `~/iot23_da_loc_01`, thư mục sàng lọc, bản kiểm kê và archive.
Bản sửa kiểm checksum của CSV, chỉ mục nhãn và PCAP đã hoàn tất trước khi
dùng lại. Nó chỉ chấp nhận nâng cấp từ đúng phiên bản công cụ đã phát hành;
không bỏ qua kiểm tra đầu vào hoặc nhận tùy ý checkpoint của công cụ khác.
Báo cáo cũ được giữ ở `BAO_CAO_XUAT_TRUOC_SUA_DUOI.json`.

CSV và PCAP đã hoàn tất được giữ nguyên. PCAP 39 đang dở sẽ được lọc lại;
không xuất lại toàn bộ CSV. Lượt 2 vẫn phải đọc lại archive từ đầu để tới
capture 39, nên số `Archive pass 2/2` có thể bắt đầu lại gần 0. Các dòng
`Reusing completed` cho biết công cụ đang dùng lại kết quả cũ.

## Cách xử lý phần đuôi thiếu

Sau khi kiểm tra kích thước nguồn và các header, công cụ giữ những bản ghi
gói hoàn chỉnh, bỏ bản ghi cuối thiếu và ghi rõ offset, số byte còn lại,
số byte thiếu cùng checksum phần bị loại trong `source_tail_excluded`.
Không thêm byte để tạo gói mới, không gán nhãn cho gói thiếu. Header và dữ
liệu của những gói được xuất vẫn nguyên byte.

PCAP sai kích thước, không có gói hoàn chỉnh hoặc có header lỗi vẫn dừng.
PCAP SYN flood đã duyệt vẫn phải khớp đầy đủ checksum và 40.568 gói; không
dùng cơ chế bỏ đuôi để chấp nhận một bản SYN khác.

Sau khi xong, báo cáo có `status: complete` cho công việc xuất và đồng thời
ghi `source_packet_records_complete: false` nếu nguồn có đuôi thiếu. Trang
HTML hiện rõ cảnh báo nguồn; danh sách tệp vẫn nằm trong
`~/iot23_da_loc_01/DANH_SACH_TEP.csv`.

```bash
xdg-open ~/iot23_da_loc_01/MO_DU_LIEU_DA_LOC.html
```
