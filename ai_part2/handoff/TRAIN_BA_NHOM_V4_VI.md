# Train model V4 từ ba nhóm PCAP đã chuẩn bị

Gói này tạo model **mới**, giữ nguyên model V3 và các dữ liệu đã lọc.
Đầu vào là ba thư mục `binh_thuong`, `syn_flood`, `vertical_scan` trong
`~/iot23_da_loc_01`, cùng các báo cáo checksum đã được tạo ở bước trước.

## Chạy trên toàn bộ dữ liệu trong máy ảo của bạn

1. Tải [train_ba_nhom_v4.zip](https://github.com/nhudaohaidang-glitch/DoanHTS/blob/ai-part2-starter-20261029/train_ba_nhom_v4.zip), bấm **Download raw**.
2. Giải nén trong Downloads của Ubuntu thành `train_ba_nhom_v4`.
3. Chạy:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/train_ba_nhom_v4/TRAIN_BA_NHOM.py
```

Công cụ kiểm checksum, trích sáu đặc trưng, train mạng 6–8–3, lượng tử hóa,
xuất model và project Gowin vào thư mục mới `~/iot23_train_v4_01`.
Không đọc lại archive gốc. Chuẩn bị đặc trưng từ các PCAP bình thường lớn
có thể lâu; tiến trình hiển thị theo từng nguồn. Dữ liệu metadata được sắp
xếp trên đĩa, không giữ toàn bộ gói tin trong RAM.

Khi bị ngắt, chạy lại đúng lệnh. Công cụ kiểm và dùng lại những nguồn đã
trích đặc trưng xong; phần đang dở được làm lại. Nếu đang fit model mà bị
ngắt, lần sau chỉ fit lại từ các đặc trưng đã có.

```bash
xdg-open ~/iot23_train_v4_01/MO_KET_QUA_TRAIN.html
```

## Đầu ra

```text
~/iot23_train_v4_01/
├── features/<source_id>/features.csv.gz
├── features/<source_id>/patterns.sqlite
├── candidate_v4/
│   ├── model/model.json
│   ├── model/float_model.json
│   ├── model/metrics.json
│   ├── model/FREEZE.json
│   ├── model/w1.hex, w2.hex, b1.hex, b2.hex, quant_params.vh
│   ├── model/vectors.txt
│   └── gowin/
│       ├── ai_core_v4.gprj
│       ├── src/ai_core_model_v4.v
│       ├── firmware/ai_quant_v4.h
│       ├── firmware/ai_v4_integration.h
│       └── verification/run_sim.sh
├── TRAIN_STATE.json
└── MO_KET_QUA_TRAIN.html
```

Nếu Ubuntu đã có Icarus, công cụ tự chạy kiểm RTL và ghi kết quả. Nếu chưa
có, model vẫn được xuất, báo cáo ghi rõ mô phỏng chưa chạy; có thể chạy
`bash candidate_v4/gowin/verification/run_sim.sh` khi đã cài Icarus.
Gowin synthesis/timing và thử trên bo chưa được công cụ này thực hiện.

## Quy tắc dữ liệu và học

- PCAP được kiểm theo checksum trong báo cáo gốc. CSV flow không được đưa
  trực tiếp vào model; công cụ đọc lại gói tin và timestamp để tính đặc trưng.
- Normal: dùng PCAP Benign đã lọc. Mỗi IP đích /32 là một bên nhận riêng;
  hai chiều trong một PCAP có thể tạo mẫu cho hai bên nhận khác nhau.
- SYN flood: chỉ đích và thời gian của đoạn capture 34 đã kiểm chứng.
- Vertical scan: chỉ IP đích bị quét và khoảng SYN đang hoạt động. Không
  gán nhãn tấn công cho những giây chỉ còn phản hồi muộn.
- Chỉ giữ cửa sổ một giây trọn vẹn, không rỗng. Một gói vẫn hợp lệ dù q0=0.
- Đếm IP/cổng phân biệt chính xác; IPv4 Total Length; SYN=1, ACK=0; giữ
  nguyên sáu đặc trưng và divisors `[8,2,1,1,1,1]` như V3.
- Để tránh đếm lặp bản cắt PCAP phụ, chọn tệp gốc lớn nhất trong mỗi thư
  mục nguồn trước khi xem đặc trưng. Các thư mục phiên Somfy khác nhau
  vẫn được giữ riêng. Mọi tệp phụ bỏ qua được liệt kê trong báo cáo.
- Mọi cửa sổ hợp lệ đều được đếm và ghi ra CSV. Khi fit, gom các điểm q
  trùng, lấy tối đa 5.000 điểm q phân biệt mỗi lớp bằng reservoir cố định,
  rồi lặp để cân bằng ba lớp. Không coi số lần lặp là dữ liệu mới.
- Seed=23, alpha=0.01, solver=lbfgs, tối đa 1.600 vòng, một cấu hình cố
  định. Không chọn model dựa vào một tập test đã xem.

## Cách hiểu kết quả

SYN flood hiện chỉ có một đợt; vertical scan cũng chỉ có một lần quét.
Vì vậy toàn bộ dữ liệu được dùng để học và báo cáo **độ khớp trên dữ liệu
học**, không tạo train/test ngẫu nhiên theo giây rồi gọi đó là kiểm thử
độc lập. Không khẳng định V4 tốt hơn V3 từ các số này.

Khi cùng một vector q có nhiều nhãn, báo cáo ghi `conflicting_quantized_patterns`
và `conflict_examples`, giữ nguyên các nhãn nguồn. Một bộ phân loại dùng
chỉ sáu giá trị giống nhau không thể trả hai nhãn khác nhau cho chúng.
Model được đánh dấu `needs_label_review` khi có xung đột; cần kiểm tra
các cửa sổ liên quan trước khi dùng nó để quyết định chặn.

Trong lần train tham chiếu trên các nguồn đang có tại đây, đã thấy 11 cửa
sổ Benign có q giống 21 cửa sổ SYN flood. Các đích Benign liên quan gồm
1.1.1.1 và 50.50.50.53. Không tự đổi nhãn hoặc bỏ các mẫu này để nâng điểm.
Kết quả đầy đủ trên thư mục của bạn có thể có thêm các xung đột khác.

Lưu lượng đã lọc có thành phần khác capture gốc đầy đủ. Khi ghép phần cứng,
người 1/3 phải thống nhất đích bảo vệ, chiều ingress và mốc cửa sổ. Dữ liệu
Somfy nào đã đưa vào học thì không còn là test độc lập của model này.
Cần thêm các phiên mới của từng lớp để đánh giá riêng trước khi dùng thực tế.

## Model tham chiếu có sẵn trong ZIP

`MODEL_THAM_CHIEU/` là model đã train tại môi trường chuẩn bị, từ các PCAP
đang có ở đây: Normal Hue4 + phần Benign capture34, SYN34 và mẫu quét công
khai Chris Sanders. Nó không phải model đã học toàn bộ 23 nguồn trên máy
ảo của bạn. Phạm vi, số cửa sổ, lỗi và kiểm RTL nằm trong báo cáo kèm theo.

Lệnh ở đầu tài liệu train lại từ đúng bộ ba thư mục trên máy bạn và tạo
model riêng. Mỗi model có checksum; khi ghép, dùng core, header và trọng số
của cùng một model. Phần cứng vẫn cần chính sách CPU/whitelist/xác nhận;
class_id đơn lẻ chưa đủ để quyết định chặn IP.
