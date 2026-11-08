# Model V5 đã train từ đúng cache của bạn

Không cần train lại. Giải nén gói `model_v5_cung_du_lieu.zip`, rồi mở
`MO_KET_QUA_V5.html` bằng trình duyệt. Giữ thư mục đã giải nén nguyên cấu trúc
để các liên kết model, báo cáo và project hoạt động.

## Đúng những dữ liệu nào?

Cache `CACHE_V4_DE_TRAIN_TIEP.zip` bạn gửi chứa đủ các cặp (nhãn, q) và số lần
xuất hiện từ 28 PCAP Normal IoT-23, một PCAP SYN flood capture 34, và đúng PCAP
vertical scan Chris Sanders đã gửi trước đó. Danh sách 30 tệp và checksum nằm
trong `V5_STATE.json` → `base.original_sources`.

Đã kiểm checksum và chạy model V4 trên toàn bộ cache, tái hiện chính xác ma
trận lỗi V4 trước khi học. Đây là học từ cache đặc trưng thực tế của bạn;
không phải đọc lại 30 PCAP lớn tại đây. Cache được gom theo (nhãn, q), có đủ
tần suất để tính lại kết quả trên mọi cửa sổ. Như V4, bước fit cân bằng các
mẫu q khác nhau giữa ba lớp; không lặp 39 triệu dòng Normal trong bộ nhớ.

- Model V4 gốc: `51050d9c05fbbbdda6cca1e21f26366ffcfeddbe7e3a01479a38eb70e790d906`.
- Cache gốc: `b76850743125c9b68c9d2419200515de9e7d53a326993532d768c6671d882e76`.
- Model V5 mới: `688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e`.

## Kết quả so sánh

| Dữ liệu có nhãn | Số cửa sổ | V4 đúng | V5 đúng, số nguyên |
| --- | ---: | ---: | ---: |
| Normal gốc | 39.253.935 | 39.253.923 | 39.253.923 |
| SYN flood gốc | 21 | 21 | 21 |
| Vertical scan gốc | 4 | 4 | 4 |
| Scan biến thể dùng thêm để học | 1.423 | 936 | 1.423 |

Vẫn có 12 cửa sổ mang nhãn Normal bị nhận SYN: precision SYN theo nhãn gốc
là 21/33 = 63,64%, dù accuracy chung rất cao do Normal chiếm gần hết dữ liệu.
V5 sai đúng 12 cửa sổ cũ, không phát sinh cửa sổ sai mới trên cache gốc.
Xem `12_CUA_SO_V4.csv`, `12_CUA_SO_V5.csv` và `RA_SOAT_NHAN.json`.

11 cửa sổ Normal và 21 cửa sổ SYN có cùng q. Log nguồn của các flow liên quan
đến 12 cửa sổ vẫn ghi Benign. Có cả đầu vào raw trùng nhau giữa Normal và SYN.
Giữ nguyên mọi nhãn, không xóa các điểm khó để tăng kết quả; sáu giá trị
đầu vào giống nhau không cho phép model phân biệt hai ý định khác nhau.

## Đã bổ sung và kiểm gì?

28 biến thể chỉ làm chậm timestamp 2–128 lần và lệch mốc thời gian của chính
PCAP scan gốc; giữ nguyên byte của cả 2.011 frame, IP, cổng và thứ tự. CSV
trong `code/examples/scan_time_variants_v5/features/` là sáu đặc trưng mỗi
giây, khác với CSV flow của bộ lọc ban đầu. PCAP nằm trong thư mục `pcap/`
cùng cấp; `AUGMENTATION_MANIFEST.json` ghi nguồn và checksum từng tệp.

Có 1.423 cửa sổ đủ điều kiện học. 192 cửa sổ chỉ thấy 1–2 cổng được lưu lại
và ghi cần ngữ cảnh nhiều cửa sổ; không đưa vào fit và không đổi thành Normal.
Tất cả biến thể thuộc cùng **một phiên scan gốc**, không tạo phiên độc lập mới.

V5 vẫn là mạng 6–8–3, divisors `[8,2,1,1,1,1]`. Đã học một model float mới
trên cache gốc cộng scan biến thể, rồi hiệu chỉnh thang từng neuron để xuất
trọng số int8 cho core cũ. Chọn giữa 40 cách lượng tử hóa trên cache học,
không dùng các vector tình huống để fit hoặc chọn lượng tử hóa. Không đổi
thứ tự sáu đặc trưng, cách đóng gói hay giao diện core.

- 36 vector tình huống đã kiểm trước đây: V5 đạt 36/36; V4 đạt 21/36.
  Đây là kiểm tra phát triển, không phải dữ liệu mạng test độc lập.
- RTL khớp Python trên 1.896 vector, thêm 1.069 vector kiểm số học độc lập;
  84 chu kỳ từ nhận `start` đến `done`. Xem `verification_extra/RESULT.json`.
- Header C biên dịch và liên kết RV32I/ILP32 thành công; chưa chạy trên CPU/bo.
- Kiểm lại 14 ca kiểm thử liên quan đến cache, trích đặc trưng, nguồn scan,
  lượng tử hóa và xuất Gowin đều đạt.

Đây vẫn là **độ khớp trên dữ liệu học/phát triển**. Chưa có các phiên SYN/scan
độc lập để đo khả năng phát hiện ngoài dữ liệu đã học. Chưa đo timing trên bo
hoặc kiểm chặn Ethernet; chưa dùng `class_id` đơn lẻ để tự động chặn mạng.

## Dùng tệp nào?

- Mở báo cáo: `MO_KET_QUA_V5.html`.
- Model và trọng số: `candidate_v5/model/`.
- Project core Gowin: `candidate_v5/gowin/ai_core_v5.gprj`.
- RTL core: `candidate_v5/gowin/src/ai_core_model_v5.v`.
- Header tích hợp: `candidate_v5/gowin/firmware/ai_quant_v5.h` và
  `ai_v5_integration.h`; cửa sổ có ít hơn 8 gói vẫn hợp lệ dù q0 bằng 0.
- Bản V4 và cache đã nhận được giữ riêng trong `V4_GOC/`.

Project Gowin chỉ chứa core AI, chưa phải bitstream firewall hoàn chỉnh.
Khi ghép core vào hệ thống, dùng các trọng số, RTL và header cùng phiên bản;
đích nhận /32 và mốc cửa sổ 1 giây phải khớp bộ trích đặc trưng.

## Nếu cần tự chạy lại

Model trong gói đã sẵn sàng để kiểm tra, không cần làm bước này để mở kết quả.
Sau khi giải nén vào `~/Downloads/model_v5_cung_du_lieu`, có thể tạo một ứng
viên khác ở thư mục mới bằng:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/model_v5_cung_du_lieu/code/tools/train_from_v4_cache.py \
  --base-v4 ~/Downloads/model_v5_cung_du_lieu/V4_GOC \
  --output ~/iot23_train_v5_01
```

Không ghi đè V4 hoặc ứng viên V5 đã có. Phiên bản thư viện dùng cho model
trong gói được ghi trong `candidate_v5/model/metrics.json`; phiên bản khác
có thể làm trọng số mới khác. Chưa có Icarus thì script ghi rõ chưa kiểm RTL.

Để chỉ kiểm toàn vẹn tệp trong gói bằng Python chuẩn:

```bash
python3 ~/Downloads/model_v5_cung_du_lieu/KIEM_TRA_GOI.py
```
