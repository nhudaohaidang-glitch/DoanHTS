# Phần 2 — mã train và dữ liệu AI V6

Gói này chỉ có mã/dữ liệu của phần AI. Để ghép vào hệ thống, người nhận dùng gói chính `phan2_ai_v6_ban_giao.zip`; không cần chạy train lại. Model đã chốt nằm tại `frozen/model.json`, SHA256 `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`.

## Dữ liệu có trong gói

- `cache/native_patterns.sqlite`: các q duy nhất cùng số lần xuất hiện của 28 Normal IoT-23, SYN capture 34 và scan Chris Sanders; giữ đủ số mẫu/nhãn gốc.
- `cache/v5_patterns.sqlite`: thêm các biến thể thời gian scan đã dùng ở V5. Cache không phải PCAP tái dựng. Danh sách 30 nguồn và checksum nằm trong `cache/V5_STATE.json` và `DATA_PROVENANCE.json`.
- `sources/`: PCAP đã lọc Normal34, SYN34 và mẫu vertical scan Chris Sanders. Không đóng gói lại toàn bộ PCAP Normal hàng chục GB; các nguồn đó đã được lưu bằng cache đặc trưng và provenance.
- `data/pcap/`, `data/features/`: 120 profile mô phỏng có PCAP và CSV sáu đặc trưng, có nhãn/trạng thái/counter để đối chiếu.
- `runtime/part2/features.py`: bộ trích đặc trưng ngoại tuyến từ PCAP của phần AI; không phải RTL trích đếm phần cứng của P3.
- `frozen/`: trọng số, metrics, tham chiếu số nguyên và báo cáo model đã chốt.

Các profile đổi thời gian hoặc trộn nền có kiểm soát từ cùng các nguồn, giữ nguyên byte gói tấn công. Nền lấy SYN-ACK/ACK NativeBenign từ Normal34, đổi địa chỉ/cổng và tính lại checksum. Chúng không phải 120 phiên thu mạng độc lập.

SYN train dùng 12.000 gói đầu, development dùng 12.000 gói tiếp theo của cùng đợt. Scan dùng cùng nguồn với các hệ số thời gian khác nhau. Cửa sổ SYN dưới 20 gói tấn công hoặc scan dưới ba cổng tấn công được giữ là cần ngữ cảnh, không đổi nhãn thành Normal. Các q dẫn xuất trùng nhãn gốc khác bị loại khỏi fit/selection và vẫn được báo riêng trong metrics.

## Chạy trên Ubuntu

Mở terminal tại thư mục gói đã giải nén. Dùng venv AI đã có nếu đủ thư viện; xem `LIBRARY_VERSIONS.json`. Nếu cần môi trường mới, bản tái tạo đã kiểm dùng Python 3.12:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-reproduce.txt
.venv/bin/python test_data.py
.venv/bin/python evaluate_historical_lab.py
.venv/bin/python train.py --output ~/iot23_v6_ung_vien_moi_01
```

Không ép các phiên bản này vào Python 3.14. Môi trường khác phiên bản có thể cho trọng số khác. Lệnh train tạo thư mục mới, mặc định alpha = .01, seed = 5, không sửa `frozen/`. Kết quả nằm tại `<output>/a0.01_s5/model.json`. Trong môi trường ghi nhận, lệnh này tái tạo đúng hash model đã chốt.

`train.py --search --output <thư_mục_mới>` lặp đủ 27 ứng viên float và 40 lựa chọn lượng tử hóa cho mỗi ứng viên; có thể chạy lâu. Các q duy nhất được cân bằng giữa lớp khi fit; lặp điểm không tạo thêm phiên lưu lượng. 36 vector kiểm phản ứng không tham gia train.

Nếu cần tái tạo 120 profile từ ba PCAP nguồn:

```bash
.venv/bin/python prepare_data.py --output ~/iot23_v6_du_lieu_tai_tao_moi_01
```

CSV flow Zeek ban đầu dùng lọc/nhãn, không phải CSV sáu đặc trưng model. Bài `test_data.py` kiểm checksum/byte tấn công, trích lại đặc trưng và giữ nguyên số mẫu/lỗi nhãn gốc. `evaluate_historical_lab.py` chỉ kiểm hồi quy V6 trên lab cũ: 218/219, một Normal nhận thành scan. Bản tách này không cần core hoặc source của các thành viên khác.

## Khi muốn đổi model

Giữ nguyên gói đã chốt và tạo ứng viên riêng. Nếu chọn trọng số mới, phải xuất đồng bộ RTL/header/vector rồi lặp bài kiểm số học và kiểm toàn hệ thống ở người tích hợp. Không chỉ chép `model.json` mới vào gói bàn giao cũ. Các công cụ xuất RTL tham chiếu của phần AI có tại `ai_part2/tools/prepare_gowin.py` trong kho DoanHTS; gói này chỉ tái tạo model/dữ liệu.

Đọc `GIOI_HAN_MODEL.md`. Độ khớp tập học/development và hồi quy lab cũ không phải kết quả kiểm lưu lượng độc lập mới.
