# Làm AI v2 sau khi challenge01 chỉ đạt 71,43%

Mục tiêu: khắc phục thiếu dữ liệu phát triển cho retry bình thường và quét chậm; đo lại trên phiên mới. Chưa có kết quả accuracy v2 thực đo. Mọi fixture trong kiểm thử phần mềm là dữ liệu nhân tạo để kiểm code, không phải chứng minh đạt 95%.

## 1. Cập nhật mã, giữ nguyên v1 và PCAP

Tải ai_v2_update.zip trên nhánh ai-part2-starter-20261029, bấm Download raw. Giải nén vào Downloads; bên trong ai_v2_update có apply_update.py và payload.

Dừng dashboard bằng Ctrl+C ở Terminal đang chạy dashboard. Không dùng sudo cho hai lệnh cập nhật:

```bash
python3 ~/Downloads/ai_v2_update/apply_update.py --target ~/ai_part2
python3 ~/Downloads/ai_v2_update/apply_update.py --target ~/ai_part2 --apply
```

Updater sao lưu code cũ dưới build/update_backups, kiểm checksum, không ghi đè data/, .venv/ hoặc model/metrics/features trong build/. Không chép lại toàn bộ kit đè lên thư mục đã làm.

## 2. Thu dữ liệu phát triển v2

```bash
cd ~/ai_part2
sudo bash lab/collect_v2.sh dev v2dev01
```

Khoảng 8–10 phút tùy máy: 20 phiên, mỗi phiên 20 giây, 10 train và 10 validation. Có MQTT bình thường một/hai nguồn, payload lớn, retry bình thường, SYN nhiều tốc độ và quét chậm/nhanh. Các tham số train và validation khác nhau; không chia cửa sổ ngẫu nhiên trong cùng capture.

Chương trình tạo lại CHỈ lab namespace thuộc bộ mã trước MỖI phiên; dừng các tiến trình lab cũ. Không chạy song song một lệnh capture khác. Nếu chưa có lab, chương trình tự dựng. Không cần chạy setup_lab.sh up trước. Marker không hợp lệ/tên namespace đã bị ứng dụng khác chiếm thì chương trình dừng. Không đổi firewall hoặc SYN cookies của máy chủ.

Đường dẫn mới: data/v2_development/v2dev01/. Hai manifest cũ data/captures/manifest.csv và data/challenge/manifest.csv không đổi. Mỗi phiên kiểm 0 kernel drops; thiếu thống kê/mất gói thì dừng. Khi lỗi, giữ thư mục cũ để kiểm tra, dùng prefix v2dev02 nếu cần thu lại cả bộ. Không xóa phiên để lấy kết quả đẹp hơn.

Kết thúc thành công có COMPLETE.json. Xem lại:

```bash
grep -H "dropped by kernel" data/v2_development/v2dev01/*/capture.log
```

Tham số PPS là giới hạn yêu cầu, không bảo đảm tốc độ thực đạt được. Bộ phát mới không gửi dồn để bù sau khi VM bị tạm dừng. Giới hạn vẫn là đích lab cố định, không uplink, tối đa 500 PPS và 60 giây; không phải phép kiểm Ethernet 100 Mbps.

## 3. Trích xuất, huấn luyện riêng và kiểm RTL

Không dùng sudo:

```bash
bash scripts/run_v2_development.sh v2dev01
```

Script dùng .venv, trích đặc trưng sang build/v2_features_v2dev01.csv, huấn luyện riêng build/lab_model_v2/, chạy mô phỏng RTL rồi in metrics validation. Chi tiết nằm trong build/v2_training_v2dev01.log. Nếu script lỗi, dừng và gửi lỗi; không tự đổi nhãn/hash để vượt kiểm tra.

V2 vẫn raw features theo spec/FEATURES_V0.md: 6 đặc trưng, cửa sổ 1 giây, đếm exact. Divisors cố định [8,2,1,1,1,1] thay v1 [8,1,1,1,1,4]; q=clamp(raw//divisor,0,127). Số cổng 2 và 6 được giữ thành 2 và 6. Đặc trưng số lượng lớn có thể bão hòa, có thống kê trong báo cáo. Điều chỉnh này đã được chọn trước khi thu v2; không chọn theo test cuối.

Kiến trúc 6–8–3 và RTL MAC/FSM không đổi. Ba seed (11,23,47) được fit trên train; chọn bằng macro-F1 SỐ NGUYÊN trên validation, hòa thì FPR nhỏ hơn, rồi theo thứ tự seed. Không chọn seed bằng test. Baseline cũng chỉ chọn trên validation. Script ghi model.json, HEX, vectors, metrics.json và FREEZE.json.

Gửi ảnh đoạn VALIDATION ONLY và PASS vectors. Accuracy ở đây là validation đã dùng chọn mô hình, chưa phải test độc lập. Nếu kết quả kém, điều tra và sửa trên dữ liệu phát triển; chưa thu holdout để tránh dùng test làm dữ liệu chỉnh mô hình.

## 4. Thu bộ kiểm tra cuối SAU khi chốt v2

Chỉ tiếp tục khi đã xem validation và quyết định giữ nguyên model. Không huấn luyện thêm sau khi thu bộ này.

```bash
sudo bash lab/collect_v2.sh holdout v2test01
bash scripts/run_v2_holdout.sh v2test01
firefox build/v2_holdout_eval_v2test01/report.html
```

Khoảng 5 phút để thu 10 phiên mới. Dữ liệu lưu data/v2_holdout/v2test01/. Trước tạo lưu lượng, collector ghi COLLECTION.json chứa hash model, hash metrics, baseline, kế hoạch phiên và thời gian bắt đầu. Eval từ chối model khác, dữ liệu thu trước record, capture ID khác kế hoạch hoặc PCAP trùng development. Không tự sửa FREEZE/COLLECTION để bỏ qua kiểm tra.

Báo cáo có accuracy, macro-F1, FPR, recall từng lớp trong metrics.json, confusion matrix, thống kê từng capture và dự đoán từng cửa sổ. Ghi cả AI và baseline; nếu baseline bằng hoặc hơn thì báo đúng. Các cửa sổ cùng phiên có tương quan; 10 phiên lab không chứng minh chất lượng mọi mạng hoặc IoT-23. Đây là phát hiện kịch bản theo cửa sổ; không phải tỷ lệ chặn từng gói hay tốc độ phát hiện toàn hệ thống.

Nếu sửa model sau khi xem holdout, kết quả đó trở thành dữ liệu phát triển; cần giữ lại và thu holdout mới trước kết luận phiên bản tiếp theo. Không chỉ chạy lại cùng dữ liệu rồi gọi là test mới.

## 5. Xuất Gowin v2 sau khi đánh giá

```bash
.venv/bin/python tools/prepare_gowin.py --model build/lab_model_v2 --output build/gowin_ai_v2
bash build/gowin_ai_v2/verification/run_sim.sh
```

Sang Windows dùng build/gowin_ai_v2/ai_core_v2.gprj. Chỉ chạy Synthesize cho core riêng; không Run All/nạp core riêng với 103 tín hiệu I/O thành chân kit. Phải kiểm timing sau ghép và route để kết luận clock thật. Thay weights có thể làm đổi tài nguyên/timing; không dùng báo cáo v1 cho v2.

Gửi người 1 firmware/ai_quant_v2.h và model/manifest tương ứng. Người 3 giữ đúng ngữ nghĩa raw counts; nếu họ tự lượng tử trong RTL thì phải cập nhật divisor v2 đồng bộ. Dùng đúng MỘT ai_core trong project, không ghép cả RTL v1 và v2. Bản v1 và công cụ bàn giao v1 cũ vẫn được giữ nguyên.

## Giới hạn phải nhớ

Một tỷ lệ SYN cao có thể do ứng dụng hợp lệ thử kết nối lại; sáu đặc trưng không luôn xác định ý đồ. Các kịch bản train/val/holdout ở đây vẫn giới hạn trong lab MQTT, retry tới một dịch vụ đóng và vertical scan. Chưa đánh giá lưu lượng hợp lệ tới nhiều dịch vụ, quét dưới 5 cổng/giây, nhiều kẻ tấn công, IP spoofing hoặc generalization sang IoT-23. Packet filter/chọn IP, TTL/whitelist và đo ảnh hưởng dịch vụ cần kiểm riêng khi tích hợp nhóm.
