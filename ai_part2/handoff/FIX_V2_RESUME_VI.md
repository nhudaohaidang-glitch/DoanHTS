# Sửa lỗi Existing veth name và tiếp tục v2dev01

Lỗi ở bước 7 không phải lỗi AI. Script teardown cũ gửi TERM rồi xóa tên namespace nhưng không xóa trực tiếp các đầu veth phía host. Một tiến trình chưa thoát có thể giữ namespace không còn tên và các veth còn tồn tại; lần up kế tiếp dừng với Existing veth name. Ownership marker cũng đã bị xóa, nên down thông thường không xử lý được trường hợp này.

Bản sửa xóa rõ ba đầu veth của lab trước khi bỏ marker, kiểm tra cleanup hoàn tất và dọn các đầu veth đã tạo nếu up bị lỗi. Có gắn owner alias cho các giao diện mới. Resume giữ nguyên sáu phiên đã đăng ký, xác minh tham số/PCAP/log capture và chỉ chạy phần còn thiếu. Nó giữ nguyên COLLECTION.json ban đầu, kể cả thời điểm và hash model của holdout.

## Cài bản sửa

Tải v2_resume_fix.zip từ nhánh ai-part2-starter-20261029, bấm Download raw, giải nén vào Downloads. Không dùng sudo cho cập nhật code:

```bash
python3 ~/Downloads/v2_resume_fix/apply_update.py --target ~/ai_part2
python3 ~/Downloads/v2_resume_fix/apply_update.py --target ~/ai_part2 --apply
```

Updater chỉ cài code/tài liệu, sao lưu file cũ; không ghi đè PCAP, manifest, model hoặc .venv.

## Tiếp tục từ phiên còn thiếu

```bash
cd ~/ai_part2
sudo bash lab/collect_v2.sh dev v2dev01 --resume
```

Dự kiến sáu dòng KEEP, rồi [7/20] v2dev01_train_syn_mid. Khoảng 5–7 phút cho 14 phiên còn lại. Bộ sửa tự kiểm tra các đầu veth mồ côi: yêu cầu COLLECTION.json đúng kế hoạch của kit, không có named lab namespace/bridge, chỉ xử lý các tên p2brokerh/p2sensorh/p2sourceh có loại veth, không gắn bridge và không có owner khác. Nếu điều kiện không khớp thì dừng để kiểm tra, không xóa giao diện khác.

Nếu có ERROR mới, gửi toàn bộ dòng lỗi; chưa chạy huấn luyện. Nếu có thư mục capture dở chưa đăng ký, giữ lại để xem nguyên nhân; resume sẽ từ chối ghi đè.

## Khi đủ 20 phiên

```bash
bash scripts/run_v2_development.sh v2dev01
```

Không dùng sudo cho huấn luyện. Gửi phần PASS vectors và VALIDATION ONLY. Chưa thu holdout cho tới khi quyết định chốt model. Collection is incomplete trước đó là kiểm tra đúng: bộ train/validation chưa đủ, không phải một lỗi mô hình mới.

## Phạm vi kiểm chứng bản sửa

Kiểm thử Bash bằng ip giả đã tái hiện điều kiện veth còn tồn tại sau xóa tên namespace và chạy up/down/up/down thành công với teardown mới. Kiểm thử lỗi ở phiên 7, tiếp tục giữ nguyên sáu phiên và COLLECTION.json, thu đúng 14 phiên còn lại. Kiểm tra recovery từ chối giao diện gắn bridge, namespace còn sống và kế hoạch bị thay đổi. Cloud không có quyền tạo namespace mạng thật; cần chạy trên Ubuntu của người dùng để xác nhận thực tế.
