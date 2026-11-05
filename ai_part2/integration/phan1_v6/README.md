# Bàn giao AI V6 + bản ghép Phần 1

V6 đã train tiếp từ đúng ba nhóm đang dùng: Normal IoT-23, SYN flood capture34 IoT-23 và vertical scan Chris Sanders. Đã khắc phục trường hợp SYN khoảng 400 gói/cửa sổ trong demo của người 1. Model, RTL và firmware mới đã ghép và vượt qua mô phỏng toàn hệ thống. Đây là gói bàn giao để nhóm tích hợp, chạy Gowin và kiểm trên bo; chưa xác nhận hoạt động trên bo thật.

## Bắt đầu trên Ubuntu

Giải nén `ghep_phan1_ai_v6.zip` vào Downloads, tạo thư mục `ghep_phan1_ai_v6`, giữ riêng bản V5 và bản gốc người 1. Chạy:

```bash
python3 ~/Downloads/ghep_phan1_ai_v6/KIEM_TRA_GHEP_V6.py
```

Lệnh kiểm toàn vẹn mọi file, chạy 3.762 vector qua bus, firmware RV32I POST 37/37 (36 lần suy luận + một cửa sổ rỗng bỏ qua), và 5 cửa sổ kiểm bộ trích đặc trưng tham chiếu. Cần Python3 và Icarus (`iverilog`, `vvp`); không cần cài thư viện AI, train lại hoặc giải nén lại IoT-23. Nếu thiếu Icarus: `sudo apt install iverilog`.

Kiểm cả demo và prototype RMII/MAC:

```bash
python3 ~/Downloads/ghep_phan1_ai_v6/KIEM_TRA_GHEP_V6.py --full
```

Có thể mất nhiều phút trên máy ảo. Đợi các bài chạy xong; không đóng terminal. Kết quả mới ở `sim/out/`; log đã đo đi kèm ở `verification/recorded/`. Mở `MO_KET_QUA_GHEP_V6.html` để xem báo cáo. `--verify-only` chỉ kiểm hash, không cần Icarus. Sau khi sửa nguồn, dùng `python3 tools/run_sim.py <tên_bài>` trong thư mục gói; kiểm toàn vẹn sẽ báo thay đổi so với bản giao ban đầu.

## Kết quả và phạm vi

- Bus: 3.762/3.762 vector đúng scores có dấu, byte enable, START khi busy và ABORT.
- CPU: POST 37/37; cửa sổ rỗng không suy luận. Cửa sổ 1–7 gói vẫn hợp lệ dù q0=0.
- Demo 40 giây: PASS; 266 khung cảm biến qua, 0 bị bỏ; chặn 1.580 khung SYN, 737 khung scan, rate-limit 779 khung SYN giả IP. TTL và gỡ chặn đạt. Các ngưỡng và chính sách gốc giữ nguyên.
- RMII/MAC tham chiếu: PASS bài chặn nguồn `.50` và chuyển cảm biến; vẫn quan sát overflow=25 trong các đợt burst. Chưa chứng minh chuyển tiếp không mất gói.
- Tập gốc: Normal 39.253.923/39.253.935; SYN 21/21; scan 4/4. Có 12 lỗi Normal theo nhãn gốc; cùng số lỗi V5 nhưng vị trí có thay đổi. Đây là độ khớp tập học.
- Development cùng nguồn: Normal 348/348; SYN 2.355/2.356; scan 640/640. Một cửa sổ 803 gói SYN bị bỏ sót. Các cửa sổ thưa/xung đột vẫn có trong CSV và thống kê riêng, không được tính là đã nhận đúng.
- Lab lịch sử: V6 218/219 so với V5 135/219; một cửa sổ reconnect Normal bị nhận Scan. Không dùng các hàng lab này để train, cũng không gọi đây là kiểm thử mới độc lập.

Một đợt SYN và một đợt scan gốc không đủ chứng minh tổng quát hóa. `ready_for_team_integration=true` chỉ xác nhận gói đủ để nhóm nhận tích hợp; `board_validated=false`, `ready_for_unattended_blocking=false` vẫn giữ rõ trong `READY_REPORT.json`.

## File giao cho từng phần

| File/thư mục | Mục đích |
|---|---|
| `rtl/part2_ai/ai_core_model_v6.v` | Core AI 6–8–3 đã nhúng trọng số, không cần đọc hex ngoài khi tổng hợp |
| `rtl/part2_ai/model.json`, `training/frozen/` | Model đã chốt, trọng số, metrics, hex và vector |
| `fw/part2/` | Lượng tử hóa C, chuẩn bị cửa sổ, tham chiếu suy luận |
| `fw/main.c`, `fw/firmware.hex`, `fw/firmware_sim.hex` | Firmware C và hai bản đã build cùng model V6; không dùng hex cũ V5/V2 |
| `rtl/wb_ai_regs.v`, `sources.f` | Bus/map thanh ghi và danh sách source của bản ghép người 1 |
| `docs/HOP_DONG_GHEP_V6.md` | Hợp đồng đặc trưng, bus, clock và việc nhóm cần xác nhận |
| `training/` | Cache gốc, PCAP/CSV đã dẫn xuất, mã train và nguồn/checksum; chỉ cần khi tái tạo hoặc cải tiến model |
| `verification/recorded/`, `INTEGRATION_REPORT.json` | Bằng chứng mô phỏng và các giới hạn còn lại |
| `reference/` | V2/V5 lịch sử, không thêm vào source active |

## Trên Windows / Gowin

Giải nén cùng ZIP vào thư mục riêng trên Windows. Mở terminal tại thư mục gói, chạy:

```text
python CHUAN_BI_GOWIN.py
```

Mở `gateway_phan1_v6.gprj`, chọn top `gowin_top`, rồi Synthesize và Place & Route. Lệnh trên tạo wrapper chỉ tới đúng firmware trên máy đó; chạy lại nếu chuyển thư mục. Mặc định `--mode mac` là MAC tham chiếu; `--mode demo` dùng traffic demo, `--mode noeth` để Ethernet nghỉ.

Clock hệ thống 27MHz, hai RMII REF_CLK 50MHz. Không dùng báo cáo tài nguyên/timing core V5 cũ để kết luận cho top V6. Cần xem timing sau P&R và CDC của top, chân/điện áp/clock PHY theo dây thực. Gói không có bitstream `.fs` cũ.

Sau Synthesize và Place & Route, chạy `python THU_BAO_CAO_GOWIN.py` ngay trong thư mục gói. Lệnh gom báo cáo tài nguyên/timing/log thành `BAO_CAO_GOWIN_V6.zip` để gửi kiểm tra, không cần tự tìm từng file. Nếu đã ghi UART từ bo, thêm `--uart đường_dẫn_file_log`. Việc gom báo cáo không tự xác nhận timing hay phần cứng đạt.

## Trước khi cắm mạng thật

Người 1 chốt cấu hình `fw/config.h`: hiện đích bảo vệ là `192.168.10.2/32`, whitelist `.2` và `.20`; cần đổi theo IP thật của broker/receiver. Sau khi đổi, build lại bằng `sh fw/build_fw.sh` với toolchain RISC-V RV32I/ILP32 rồi chạy các bài kiểm lại. Bản bo dùng TTL60s, bản mô phỏng TTL6s. Mặc định DETECT; policy xác nhận 2 cửa sổ liên tiếp, minSYN20 và minport3 được giữ nguyên. Không chặn chỉ vì một `class_id` đơn lẻ.

Người phụ trách P3 thay parser/feature/filter tham chiếu bằng module chính thức theo hợp đồng, chạy lại toàn bộ test. Người phụ trách MAC xử lý overflow và kiểm mất gói/both directions. Nhóm xác nhận POST/hash trên bo, MQTT/ARP/cảm biến, kiểm tấn công và reconnect hợp lệ có PCAP+UART, TTL/gỡ chặn. Các bước cần bo/Gowin chưa được thực hiện tại môi trường chuẩn bị gói này.

Mã model SHA256: `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`.
