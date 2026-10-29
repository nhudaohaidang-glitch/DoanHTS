# Phần người 2 — công việc sau AI v1

Bản này bổ sung dashboard, đánh giá challenge giữ nguyên model v1, bộ đo MQTT/TCP và gói bàn giao. Không huấn luyện lại v1, không tự thêm luật firewall hoặc tạo log giả làm dữ liệu kit.

## 0. Cập nhật mã trên Ubuntu, giữ nguyên dữ liệu

Tải part2_next_steps.zip từ GitHub, giải nén vào Downloads. Bên trong thư mục part2_next_steps có apply_update.py, UPDATE_MANIFEST.json và payload.

Dừng dashboard cũ nếu đang chạy. Không dùng sudo cho cập nhật mã:

```bash
python3 ~/Downloads/part2_next_steps/apply_update.py --target ~/ai_part2
python3 ~/Downloads/part2_next_steps/apply_update.py --target ~/ai_part2 --apply
```

Lệnh đầu chỉ xem danh sách thay đổi, lệnh sau áp dụng. Mã cũ được sao lưu dưới build/update_backups. Dữ liệu data/, .venv/ và build/lab_model_v1/ không bị ghi đè. Không chép nguyên thư mục mới đè lên Home nếu đã có PCAP/model.

## 1. Dashboard bằng dữ liệu thật đã thu, chưa cần kit

```bash
cd ~/ai_part2
.venv/bin/python tools/dashboard.py --session data/captures/normal_train03
```

Mở Firefox TRONG UBUNTU, nhập địa chỉ 127.0.0.1:8765 vào thanh địa chỉ (giao thức HTTP). Nếu mở từ Windows, loopback đó là Windows và có thể không tới máy ảo.

Cần thấy:
- Trái: tổng thao tác, thành công, lỗi của HAI cảm biến, bản ghi receiver và đồ thị nhiệt độ.
- MQTT FILE HISTORY: đây là phiên cũ, không hiện tuổi dữ liệu thành báo động dịch vụ hiện tại.
- Phải: CHƯA KẾT NỐI FPGA; không có log BLOCK bịa ra.
- Tổng đếm tính toàn bộ log, không cắt còn 100 dòng; chỉ lịch sử đồ thị/P95 gần đây được giới hạn.

Ctrl+C dừng dashboard. Không cần cài Node-RED để chạy bản tối thiểu này.

### Theo dõi một phiên đang chạy

Terminal 1:

```bash
.venv/bin/python tools/dashboard.py --session data/challenge/live_normal01 --live-mqtt
```

Terminal 2 (lab phải đang up):

```bash
sudo bash lab/run_capture.sh normal challenge live_normal01 30 200 0.5 2
```

Dashboard chờ file xuất hiện. Phiên mới dùng tên chưa có. FILE_HISTORY/LIVE_FILES đều là log MQTT trên máy, không chứng minh FPGA đang lọc.

### Kiểm tra giao diện log, có nhãn FILE REPLAY

```bash
.venv/bin/python tools/make_sample_log.py > build/sample_next.log
.venv/bin/python tools/dashboard.py --log build/sample_next.log --ids-schema pdf-v1 --session data/captures/normal_train03
```

Bên phải hiển thị dữ liệu mẫu có badge FILE REPLAY / KHÔNG PHẢI KIT. Dữ liệu mẫu chỉ để kiểm giao diện. Khi người 1 có log thật, dùng --serial /dev/ttyUSB0 (hoặc thiết bị thực tế), kiểm quyền dialout và USB passthrough. --ids-schema pdf-v1 chỉ dùng khi người 1 đồng ý đúng spec/LOG_SCHEMA_PDF_V1.md; mặc định IDS giữ thô. Không mở cùng cổng UART ở bootloader và dashboard.

## 2. Đo ảnh hưởng dịch vụ từ các phiên đã có

So sánh hai phiên cùng một nguồn MQTT và cùng khoảng gửi 1 giây:

```bash
.venv/bin/python tools/compare_sessions.py \
 --baseline data/captures/normal_train02 \
 --during data/captures/syn_train01 \
 --shared-clock \
 --output build/mqtt_comparison_v1.json
```

--shared-clock phù hợp lab namespace trong cùng Ubuntu. Không dùng mặc định này cho hai laptop chưa đồng bộ đồng hồ. Thời gian connect/publish/disconnect của sender không phải RTT, không phải độ trễ AI. PUBACK và số receiver nhận được được báo riêng.

Nếu cả hai phiên không có lỗi publish, báo cáo ghi chưa chứng minh gián đoạn dịch vụ. Không đổi con số để có cảnh “server sập”. Kết quả chỉ tính thao tác đã hoàn tất và ghi log; tác vụ bị kết thúc ở cuối phiên có thể chưa được đếm. Chuẩn bị nhiều lần lặp, so cùng tải MQTT để đánh giá đáng tin hơn.

Các phiên MỚI tự ghi broker_stats.jsonl: SYN_RECV và một số bộ đếm kernel (SyncookiesSent, ListenDrops...). Nếu file cũ không có thì báo broker_stats_available=false, không giả là số 0. OS có thể đang tự chống SYN flood, nên MQTT vẫn hoạt động là một kết quả cần giải thích, không tự chứng minh AI bảo vệ.

## 3. Thu bộ challenge MỚI, không trộn vào train/val/test cũ

Kiểm tra lab:

```bash
sudo ip netns list
```

Nếu ba namespace còn đủ, dùng tiếp. Nếu đã reboot và mất namespace nhưng còn marker, chạy setup_lab.sh down rồi up để dựng lại lab do bộ mã này sở hữu. Không chạy lại up trên lab đang hoạt động.

```bash
sudo bash lab/collect_challenge.sh challenge01
```

Khoảng 4 phút, 7 phiên, đích cố định trong mạng namespace không uplink:
1. MQTT hợp lệ, bản tin lớn 512 byte padding.
2. Hai nguồn MQTT hợp lệ, bản tin lớn 1024 byte padding.
3. Nguồn MQTT + đối chứng hợp lệ thử kết nối lại tới MỘT dịch vụ không sẵn sàng (TCP port 1884, tối đa 10 lần/giây). Đây là hành vi benign được kiểm soát, không gán nhãn từ dự đoán AI.
4. SYN 20 gói/giây mục tiêu.
5. SYN 400 gói/giây mục tiêu.
6. Vertical scan 5 lần/giây mục tiêu.
7. Vertical scan 300 lần/giây mục tiêu.

Tốc độ thực tế đọc PCAP/source.log, không mặc định bằng yêu cầu. Tấn công trong dữ liệu là kịch bản phát lưu lượng, không tự có nghĩa broker đã bị gián đoạn. Tool giới hạn số giây/tốc độ và đích lab, không nhận mục tiêu tùy ý.

Lưu RIÊNG data/challenge/manifest.csv; data/captures/manifest.csv cũ được giữ nguyên. Nếu chạy lặp, dùng prefix challenge02, challenge03... thay vì xóa phiên cũ. Khi lỗi, script dừng và bảo toàn dữ liệu đã thu.

Kiểm tra mất gói:

```bash
grep -H "dropped by kernel" data/challenge/*/capture.log
```

Nếu không phải 0 hoặc nguồn không chạy, xử lý trước khi dùng làm chuẩn đánh giá.

## 4. Đánh giá v1 đã đóng băng

```bash
.venv/bin/python tools/feature_quant.py \
 --manifest data/challenge/manifest.csv \
 --output build/challenge_features_v1.csv \
 > build/challenge_features_v1.log

.venv/bin/python tools/evaluate_frozen.py \
 --dataset build/challenge_features_v1.csv \
 --model build/lab_model_v1/model.json \
 --original-meta build/lab_features_v1.meta.json \
 --output build/challenge_eval_v1
```

Không gọi train.py. Eval kiểm hash model so với bản đã review, giữ luật ngưỡng cũ, từ chối PCAP trùng hash với bộ gốc. Sáu đặc trưng/counting phải đúng exact/1 giây như v1. Nếu đã đổi model.json, giữ cả hai bản và kiểm tra trước, không sửa hash để bỏ qua.

Kết quả:
- metrics.json: AI và baseline, recall từng lớp, FPR, mỗi capture, tỷ lệ bão hòa đầu vào.
- predictions.jsonl: từng cửa sổ, nhãn thật, dự đoán, score và quantized input.
- per_capture.csv: bảng theo phiên.
- report.html: mở trực tiếp bằng Firefox để đọc bảng và confusion matrix.

Có thể thấy chất lượng giảm. Đó là kết quả có giá trị. Không tự đổi nhãn hoặc chỉnh v1 rồi tiếp tục dùng cùng challenge để gọi là test độc lập. Nếu phát triển v2, cần giữ v1, chọn train/validation mới và một holdout chưa dùng cho quyết định sửa mô hình.

Chỉ sau khi có metrics thực tế mới kết luận có đạt mục tiêu 95% trong những điều kiện này. Window accuracy không phải packet blocking accuracy; các cửa sổ cùng phiên có tương quan.

## 5. Dashboard kèm kết quả đánh giá ngoại tuyến

```bash
.venv/bin/python tools/dashboard.py \
 --session data/challenge/challenge01_normal_two \
 --evaluation build/challenge_eval_v1/metrics.json
```

Dòng đánh giá ghi rõ NGOẠI TUYẾN. Chưa có log UART thì phải vẫn ghi CHƯA KẾT NỐI FPGA.

## 6. Gói bàn giao người 1 và 3

```bash
.venv/bin/python tools/make_handoff.py --output build/ai_v1_handoff_v2.zip
```

Đọc handoff/HANDOFF_PERSON1_3.md: module/ports, sáu đặc trưng, raw->quantization->packing, golden examples, trách nhiệm AI/CPU/bộ lọc, các bước kiểm tra ghép. Gói có checksum file và project Gowin theo v1. Không tự thêm tất cả module trong archive vào một project; dùng đúng một ai_core.

Phần tự làm được đã có mã; Ethernet/firmware tích hợp, timing sau routing, log kit và khả năng chặn thật vẫn cần phối hợp nhóm.
