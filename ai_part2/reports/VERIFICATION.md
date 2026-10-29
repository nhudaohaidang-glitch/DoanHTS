# Kiểm chứng trong môi trường cloud

- Nền tảng chạy thử: Linux Debian, Python 3.12; numpy 2.2.6, scikit-learn 1.6.1, Scapy 2.6.1, Paho MQTT 2.1.0; Mosquitto 2.0.21, Icarus Verilog 12.0.
- 8 kiểm thử Python đã PASS, gồm MQTT thật trên loopback: 3 lần connect/publish QoS1/disconnect, subscriber nhận đủ seq 0,1,2. Các test còn lại kiểm tra hướng gói, SYN không gồm SYN-ACK, phân mảnh, lượng tử hóa, trùng PCAP giữa split, số học âm/bão hòa, đóng gói và checksum log.
- Pipeline tự kiểm tra hoàn chỉnh đã chạy: 18 PCAP nhân tạo -> 360 cửa sổ -> train/val/test theo capture -> MLP -> integer model -> ROM -> RTL.
- RTL PASS 384 vector của model demo (test + vector biên/ngẫu nhiên). Thêm hai model kiểm tra số âm/bão hòa và đồng điểm: 102 + 102 vector PASS. Tổng 588 lượt so khớp điểm số/class, cùng các kiểm tra reset giữa giao dịch, start khi busy, latch feat và done một chu kỳ.
- Latency RTL mô phỏng: 84 chu kỳ. Không có kết quả timing Gowin hoặc số tài nguyên toàn thiết kế; không gọi đây là 100Mbps hoặc 3,11us đã đo trên kit.
- Model demo được ghi synthetic_only_metrics=true; metrics không đại diện độ chính xác trên mạng thật.
- Dashboard: HTTP functional request kiểm tra 7 log đúng checksum, gắn nguồn FILE REPLAY, đọc số liệu sensor/receiver. JavaScript kiểm tra cú pháp; chưa có kiểm thử giao diện bằng trình duyệt.
- Shell đã bash -n, Python đã compileall.

Chưa kiểm chứng ở cloud:
- Tạo network namespace: môi trường báo /run/netns read-only, không chạy được lab ba namespace tại đây. Script up/down/run_capture cần thực thi và kiểm tra bằng sudo trong Ubuntu của người dùng.
- apt installer trên Ubuntu 26.04: chưa có máy Ubuntu đó; dùng package kho phân phối để tương thích Python bản địa, không ép wheel Python 3.12 lên Python mới.
- Tấn công thật, broker suy giảm, độ chính xác lab thật, LAN8720, lọc trên FPGA, log thật UART, Node-RED và tích hợp firmware.

Không có mã nguồn hoặc lockfile trong checkout DoanHTS bị thay đổi. Gói này là thư mục riêng để người dùng kiểm tra rồi bàn giao nhóm.

Cập nhật AppArmor: helper chỉ sửa local include và thêm quyền đọc config phiên lab. 6 kiểm thử bổ sung PASS cho tìm include hiện đại/cũ, từ chối profile mơ hồ, thêm quyền idempotent, giữ quy tắc cũ, khôi phục khi parse lỗi và từ chối symlink thoát thư mục. Chưa nạp profile vào kernel Ubuntu thật trong cloud; cần thực thi helper trên Ubuntu người dùng.

Cập nhật đối chứng hai nguồn: bài MQTT integration đã thêm hai client hợp lệ chạy đồng thời với client ID khác nhau, kiểm tra subscriber nhận đủ các cặp sensor_id/seq; không chỉ đếm PUBACK. Đây là kiểm tra hai client trên loopback; hai IP trong namespace vẫn cần kiểm chứng ở máy người dùng bằng PCAP. Các phiên lab SYN/scan người dùng đã thu được, nhưng dữ liệu đó không có trong cloud để đánh giá model.

Cập nhật timestamp PCAP: thêm 2 regression test cho đảo thứ tự qua biên cửa sổ, SYN/SYN-ACK, giữ đủ số gói và giữ nguyên SHA256 PCAP. Kiểm tra CSV và metadata báo đảo timestamp. PCAP thực tế trên máy người dùng chưa có trong cloud; chưa xác định mức timestamp lùi của các phiên đó.

Review model lab v1 người dùng gửi: HEX khớp JSON, 360 vector tái tính khớp integer model, source RTL gốc và bản ROM nhúng đều PASS 360 vector/84 chu kỳ. C helper quantization khớp Python 204 trường hợp; Yosys 0.52 CHECK 0 problems. Không có PCAP/feature CSV trong gói để tính lại nhãn hoặc accuracy. Gói Gowin chưa chạy trên công cụ Gowin/kit. Thêm 3 test cho generator (self-contained/no overwrite, reject stale HEX, reject mismatched vectors), đều PASS.
