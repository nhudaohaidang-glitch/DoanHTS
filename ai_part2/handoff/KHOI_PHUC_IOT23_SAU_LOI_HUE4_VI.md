# Tiếp tục sau lỗi Hue4 khác hash

Báo cáo trên máy người dùng cho thấy Syn34 đã xác minh; Hue4 có tên và dung lượng đúng (4594492 byte) nhưng SHA256 là f770897e6cc3fa45857aee25ef7d3ab39dba39127b5bb813e0e0d48d3b905347, khác bản riêng đang công bố (3fb775c0391b6ad313a3f7845e634a277b07c3f6377346c2486ba63e1c22e90c). Hash khác chưa đủ kết luận archive bị hỏng. Chưa có bản Hue4 đó ở workspace để xác định byte nào khác.

Công cụ cũ dừng trước khi tạo trang kết quả, nên Firefox báo File not found. Bản mới cũng tạo trang chẩn đoán khi nguồn chưa xác minh, nhưng không cần chạy lại archive để dùng sửa đổi đó.

## Cách chạy trên Ubuntu

Giữ nguyên ~/iot23_work_01 và archive trên Windows. Không xóa chúng, không sửa hash và không chạy lại archive21 GB.

1. Tải khoi_phuc_iot23.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw.
2. Giải nén trong Downloads của Ubuntu, để có ~/Downloads/khoi_phuc_iot23/RECOVER_IOT23.py.
3. Chạy:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/khoi_phuc_iot23/RECOVER_IOT23.py \
  --work ~/iot23_work_01 \
  --output ~/iot23_khoi_phuc_01
```

Cần kết nối Internet để tải bản Hue4 riêng nếu bản cũ chưa khớp. Chỉ tải376840 byte (~377 KB), không tải lại full archive. Chương trình in tiến độ theo nguồn. Khi hiện DONE mới mở:

```bash
firefox ~/iot23_khoi_phuc_01/MO_KET_QUA.html
```

Nếu lỗi, gửi nguyên thông báo. Không xóa thư mục cũ. Khi cần chạy lại, dùng đầu ra mới như ~/iot23_khoi_phuc_02; công cụ không ghi đè đầu ra đã tồn tại.

## Dữ liệu và nguồn

- Syn34: đọc lại PCAP đã trích, kiểm kích thước và SHA256; không tin riêng trường found trong báo cáo cũ. Nếu không khớp, dừng trước khi tải.
- Hue4: nếu khớp bản đã kiểm tra thì dùng lại. Nếu khác, tải bản .xz riêng từ máy chủ chính thức, kiểm SHA256 cả file nén và file giải nén.
- Nếu có bản Hue4 cùng dung lượng nhưng khác hash trong thư mục cũ: đối chiếu từng record PCAP với bản tham chiếu, gồm link type, thứ tự, timestamp chính xác, caplen, wirelen và toàn bộ byte của từng gói. Nếu tất cả bằng nhau thì dùng lại bản đã trích, ghi rõ kiểm tra tương đương gói trong báo cáo. Một thay đổi ở global header PCAP có thể làm hash khác mà không đổi các gói; chưa kết luận trường hợp người dùng có phải như vậy hay không.
- Nếu record nào khác, không gán nhãn bản đó. Giữ nguyên và dùng bản Hue4 riêng đã xác minh làm nguồn bổ sung; báo cáo và HTML ghi rõ việc bổ sung. Không giả định rằng Hue4 bổ sung đã được trích từ archive người dùng.
- Chương trình không mở archive, sửa PCAP/báo cáo cũ, train hay đổi model. Đầu ra mới ghi hash báo cáo cũ và đường dẫn/hash từng nguồn. Giữ thư mục cũ để có thể truy ngược PCAP Syn34.

Kết quả dự kiến là2880 cửa sổ Hue4 và21 cửa sổ SYN, tổng2901. Mỗi dòng X_6_raw.csv có đúng sáu đặc trưng; X_6_fpga.csv chứa sáu q theo divisor [8,2,1,1,1,1]; y.csv riêng có0=Normal và1=đoạn SYN đã xác minh. THONG_TIN_DONG.csv ghi nguồn/thời gian.

Chỉ giữ cửa sổ đầy đủ1 giây, có gói, hướng tới IP bảo vệ. Không bỏ cửa sổ chỉ vì q0=0. Không có lớp2=vertical scan trong hai nguồn này; dự án lấy lớp đó từ lab có kiểm soát. Đây là tái lập nguồn development v3, không phải bộ train mới đủ ba lớp hoặc một test độc lập.
