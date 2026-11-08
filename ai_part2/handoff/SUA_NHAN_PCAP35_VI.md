# Sửa nhãn quá sớm, giữ nguyên dữ liệu đã trích

Kết quả người dùng:378 gói SYN khớp DDoS gốc,406 cửa sổ có gói,9 cửa sổ thuần SYN. Cả9 dòng sáu đặc trưng đều [1,60,127,1,1,1].127 là tỷ lệ SYN100%, còn cột đầu là1 gói trong một giây. Chưa đủ bằng chứng để gọi các dòng này là SYN flood, và cũng không được tự đổi thành Normal.

Phiên bản đầu TRICH_PCAP35.py đã xuất y.csv=1 quá sớm. Lỗi nằm ở việc chuyển bằng chứng packet/flow thành nhãn loại tấn công của dự án. Không chữa bằng cách tự đặt một ngưỡng PPS sau khi xem dữ liệu. Bản sửa loại bỏ việc gán nhãn tự động cho mọi mức tải; các đặc trưng và model giữ nguyên.

## Chạy sửa trên kết quả đã có

Tải sua_nhan_pcap35.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw, giải nén trong Downloads thành sua_nhan_pcap35. Chạy:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/sua_nhan_pcap35/SUA_NHAN.py \
  --input ~/iot23_pcap35_01 \
  --output ~/iot23_kiem_lai35_01
```

Công cụ chỉ dùng thư viện chuẩn và đọc CSV/báo cáo đã có. Không đọc archive hoặc PCAP, không tải dataset và không train. Bước này thường chạy nhanh vì chỉ có406 cửa sổ.

Nó sẽ:

- Giữ nguyên PCAP, log nhãn native, sáu raw, sáu q và BAO_CAO_PCAP.json cũ.
- Đổi tên y.csv tự động của bản cũ thành y_LEGACY_KHONG_DUNG_TRAIN.csv trong syn_da_kiem_tra, giữ nguyên nội dung để truy vết. Không đưa bản nhãn này vào train.
- Lưu trang HTML cũ thành MO_KET_QUA_PCAP_TRUOC_SUA_NHAN.html và thay trang mở mặc định bằng thông báo sửa nhãn. Tất cả thay đổi này có bản gốc để đối chiếu; không xóa dữ liệu.
- Sao chép các ứng viên sang ung_vien_syn_chua_gan_nhan ở thư mục kết quả mới, không tạo y.csv và không tạo nhãn0.
- Xem cả406 cửa sổ, gồm cửa sổ trộn SYN với ACK/UDP/lưu lượng khác, để báo đỉnh SYN/giây và đỉnh SYN khớp DDoS/giây. Chưa kết luận toàn capture35 không có SYN flood chỉ từ9 cửa sổ thuần SYN.

Khi DONE, gửi kết quả:

```bash
cat ~/iot23_kiem_lai35_01/TOM_TAT_SUA_NHAN.csv
```

Muốn mở bảng20 cửa sổ nhiều SYN nhất:

```bash
firefox ~/iot23_kiem_lai35_01/MO_KET_QUA_SUA.html
```

Đầu ra phải là thư mục mới. Nếu chạy lại, dùng tên ~/iot23_kiem_lai35_02. Công cụ nhận ra bản nhãn cũ đã được lưu lại và không ghi đè nó. Nếu bạn đã sửa nhãn hoặc bằng chứng khiến chúng không khớp dữ liệu cũ, công cụ dừng trước khi sửa các tệp đó; gửi thông báo lỗi để kiểm tra.

## Giới hạn và dữ liệu vẫn hợp lệ

TOM_TAT_SUA_NHAN.csv cho biết9 ứng viên có bao nhiêu gói/giây, và đỉnh SYN của cả406 cửa sổ. Các số đỉnh là bằng chứng để đánh giá tiếp, không tự quyết định nhãn flood. Cờ TCP theo ba IP đích trong JSON được giữ từ báo cáo trích trước, không giả vờ đã đọc lại PCAP ở bước sửa này.

Không sửa model v3, tập2901 dòng đã tái lập hoặc nguồn SYN capture34 đã được kiểm độc lập. Nguồn capture34 có40568 gói trong một đợt khoảng22 giây và21 cửa sổ đầy đủ, đã có quy trình review riêng; việc đó không cho phép gán tự động cùng nhãn cho bất kỳ cửa sổ SYN thuộc flow DDoS khác.

Không xác minh vertical scan trong bước này. Kết quả lọc không được bổ sung nhãn để đủ ba lớp hoặc cho đẹp số liệu. Dữ liệu chưa đủ bằng chứng được giữ chưa gán nhãn.
