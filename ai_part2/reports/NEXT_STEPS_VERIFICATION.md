# Kiểm chứng bộ công việc tiếp theo

Đã chạy trong cloud:
- 34 test PASS trên một bản sao bộ mã cũ sau khi áp dụng CHÍNH payload cập nhật. Bao gồm MQTT thật loopback (một/hai client, payload 1024 byte), parser/quantization/CRC, PCAP timestamp order, exporter Gowin, đánh giá model cố định, HTTP dashboard và updater.
- Dashboard API đọc file JSONL ghi dở mà không đếm trùng; tổng vượt 100 dòng không bị cắt; file truncate làm reset store; history không tự tạo tuổi dữ liệu live; checksum/giá trị sai bị loại; BLOCK/UNBLOCK và TTL chờ xác nhận; schema IDS chỉ diễn giải khi bật rõ.
- CLI evaluate_frozen xử lý PCAP fixture nhân tạo, tạo HTML/JSON/CSV và từ chối capture trùng hash bộ gốc. Fixture chỉ kiểm chứng chương trình, không phải kết quả accuracy mạng mới.
- Updater preview/no-op, checksum, chỉ ghi đường dẫn code được phép, sao lưu, khôi phục khi giả lập lỗi giữa chừng; .gitignore hợp nhất thêm quy tắc, giữ dòng người dùng. Thử payload thật trên snapshot HEAD cũ, giữ nguyên byte model và PCAP sentinel, chạy lại trả already_current.
- Gói bàn giao tạo được, 23 file và SHA256 từng file khớp ZIP.
- Tool đọc counter TCP chạy được ở namespace cloud hiện tại, 3 snapshot. Không phải counter broker của người dùng.
- Python compileall, bash -n và JavaScript node --check đều qua. Chưa kiểm tra hình ảnh giao diện bằng trình duyệt.

Chưa chạy trong cloud / chưa có dữ liệu:
- Không tạo được ba network namespace tại đây do hạn chế hệ thống; collect_challenge.sh, normal_probe và /proc counter trong namespace broker cần xác nhận trên Ubuntu người dùng. MQTT payload lớn được kiểm chứng trên loopback, không phải hai LAN8720.
- Chưa có PCAP challenge hoặc log sensor/receiver của người dùng trong cloud để xuất accuracy, FPR, ảnh hưởng dịch vụ hoặc độ trễ mới. Không tạo kết quả giả thay cho dữ liệu đó.
- Không huấn luyện lại hoặc thay trọng số/divisor/shift của v1. Không sửa firewall Ubuntu host, không tắt SYN cookies/AppArmor, không tự gửi lệnh chặn từ dashboard.
- Ethernet, firmware tích hợp, serial log kit, PNR và khả năng chặn thực tế vẫn chờ nhóm.
