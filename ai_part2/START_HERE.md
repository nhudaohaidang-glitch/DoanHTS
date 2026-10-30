# Bắt đầu trên Ubuntu 26.04 — làm theo thứ tự

Hướng dẫn đầy đủ: README_VI.md. Đây là bản ngắn cho buổi đầu, chưa cần Tang Nano.

1. Tải ZIP và chép/giải nén vào Home của Ubuntu để có ~/ai_part2. Không giải nén đè thư mục cũ.
2. Ctrl+Alt+T mở Terminal.
3. Chạy:

```bash
cd ~/ai_part2
bash scripts/install_ubuntu.sh
bash scripts/selfcheck.sh
```

4. Tự kiểm tra MQTT thật trên loopback:

```bash
PART2_MOSQUITTO_BIN="$(command -v mosquitto)" .venv/bin/python -m unittest discover -s tests -v
```

5. Tạo lab riêng và ghi dữ liệu bình thường:

```bash
sudo bash lab/setup_lab.sh up
sudo bash lab/run_capture.sh normal train normal_train01 20
```

6. Xem data/captures/normal_train01/sensor.jsonl và received.jsonl. Cần có bản tin gửi thành công VÀ subscriber nhận thật. Nếu lỗi dừng tại đó, không đổi nhãn dữ liệu để đi tiếp.
7. Dừng lab khi nghỉ:

```bash
sudo bash lab/setup_lab.sh down
```

Buổi sau làm SYN flood và vertical scan bằng các lệnh ở README_VI.md, rồi train trên PCAP lab thật. Bài selfcheck dùng PCAP tự tạo; không phải kết quả phát hiện 95%.

Phần đã có: PCAP->features, MLP, integer model, ai_core, testbench, sensor/broker scripts, dashboard tối thiểu.
Phần chưa có: Ethernet bridge thật và kết quả đánh giá trên kit/capture mạng thật của bạn.
