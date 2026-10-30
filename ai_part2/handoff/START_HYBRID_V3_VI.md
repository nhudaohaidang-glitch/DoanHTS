# Bản cập nhật v3 — model đã huấn luyện, bạn chạy test mới

Tải ai_v3_hybrid_update.zip từ nhánh ai-part2-starter-20261029, Download raw, giải nén vào Downloads thành thư mục ai_v3_hybrid_update. Gói có model/core v3 đã chốt, công cụ test mới và cache đặc trưng Somfy dùng kiểm tra. Không cần tải PCAP hay huấn luyện lại để chạy các bước sau.

## 1. Cài code và model v3, giữ v2

Không dùng sudo:

```bash
python3 ~/Downloads/ai_v3_hybrid_update/apply_update.py --target ~/ai_part2
python3 ~/Downloads/ai_v3_hybrid_update/apply_update.py --target ~/ai_part2 --apply
```

Updater sao lưu code cũ. Không ghi đè data/, .venv/ hoặc build/ chứa model/dữ liệu cũ. V3 nằm riêng tại gowin/hybrid_v3/. Thuật toán và model v2 được giữ làm đối chứng.

## 2. Thu test lab mới đủ ba lớp

Dừng các lệnh capture khác. Chương trình tạo lại đúng lab thuộc bộ mã mỗi phiên; không đụng mạng uplink hoặc namespace ngoài lab.

```bash
cd ~/ai_part2
sudo bash lab/collect_hybrid_v3.sh v3test01
```

Khoảng6–8phút,11phiên25giây, thêm normal_sparse có các giây không gói. Các mức tải khác bộ lab dùng phát triển. Collector chụp hash model trước khi thu, kiểm0kernel drops, lưu riêng data/v3_holdout/v3test01. Khi bị gián đoạn và chỉ còn phiên chưa thu:

```bash
sudo bash lab/collect_hybrid_v3.sh v3test01 --resume
```

Không đổi model sau khi bắt đầu test. Giữ nguyên các phiên lỗi/thành công; resume kiểm manifest, PCAP và kịch bản trước khi KEEP. Nếu có unregistered partial session hoặc ERROR mới, gửi lỗi để xử lý; không tự đổi nhãn/manifest.

## 3. Đánh giá model đã chốt

Không dùng sudo:

```bash
bash scripts/run_hybrid_v3_holdout.sh v3test01
firefox build/hybrid_v3_eval_v3test01/report.html
```

Report tách IoT‑23 Somfy benign và lab mới, có cả AI float/integer và luật ngưỡng. IoT‑23 test này chỉ có normal, không có SYN/scan. Kết quả đủ ba lớp phải dựa vào lab mới và xem bảng từng nguồn/capture, không chỉ accuracy tổng. Các giây rỗng được skip theo raw packet count, không gán normal đúng giả; report ghi số lượng. Không gọi đó là tỷ lệ chặn gói hoặc thời gian phát hiện trên bo.

Gửi ảnh các phần native benign, lab mới, tổng hợp và bảng theo phiên. Nếu model không đạt mục tiêu, giữ báo cáo; nếu sửa model sau khi xem test thì bộ này trở thành development và cần test mới.

## 4. Kiểm RTL/synthesis v3 sau đánh giá

```bash
bash gowin/hybrid_v3/verification/run_sim.sh
```

Mong đợi PASS550vectors,84cycles. Sang Windows dùng project gowin/hybrid_v3/ai_core_v3.gprj chạy Synthesize riêng; chưa RunAll/nạp core riêng. Khi ghép dùng src/ai_core_model_v3.v, firmware/ai_v3_integration.h (include ai_quant_v3.h), spec rawfeatures/interface và dữ liệu kiểm trong project. Cùng ngữ nghĩa6đặc trưng/divisorv2 nên chưa cần đổi rawfeatureRTL, nhưng phải thống nhất model/header đúng phiên bản. Xem HYBRID_V3_STATUS_VI.md.

## Tái lập huấn luyện (tùy chọn, không cần để chạy test ứng viên đã gửi)

Yêu cầu giữ CSV lab cũ trên máy: build/challenge_features_v1.csv và build/v2_holdout_v2test01.csv cùng metadata. Source nguồn chính thức và SHA nằm trong spec/HYBRID_V3_SOURCES.json. Script chỉ tải3PCAP cần thiết, khoảng0.51GB trước giải nén, có stream/hash; máy16GBRAM xử lý theo gói.

```bash
.venv/bin/python tools/download_iot23_v3.py development
.venv/bin/python tools/prepare_hybrid_v3.py
.venv/bin/python tools/train_hybrid_v3.py --dataset build/hybrid_v3_features.csv --output build/hybrid_model_v3_local
```

Không dùng kết quả Somfy đã xem để chỉnh mô hình rồi tiếp tục gọi chính nó là test độc lập. Tái train trên phiên bản thư viện khác có thể ra weights khác; phải giữ model mới riêng và freeze/test phù hợp. Script cố ý không ghi đè output đã có.
