# Bản ghép Phần 1 + AI V5 để kiểm thử

Gói này ghép đúng V5 đã train trên ba nhóm dữ liệu đã tạo vào ZIP của người 1.
Model SHA256: `688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e`.
Không train lại, không đổi nhãn, không sửa trọng số hoặc ngưỡng/chính sách chặn.

**Đã đạt kết nối số học CPU–AI; kiểm thử phát hiện toàn hệ thống chưa đạt.**
V5 vẫn nhận Normal cho đợt SYN khoảng 400 gói mỗi cửa sổ trong demo này.
Xem `MO_KET_QUA_GHEP_V5.html`, `INTEGRATION_REPORT.json` và các log đi kèm.

## Chạy kiểm tra trên Ubuntu

Giải nén ZIP vào Downloads thành `~/Downloads/ghep_phan1_ai_v5`, giữ riêng
bản gốc của người 1. Dùng Python chuẩn và Icarus đã cài, không cần train dữ
liệu hay cài thêm thư viện AI:

```bash
python3 ~/Downloads/ghep_phan1_ai_v5/KIEM_TRA_GHEP_V5.py
```

Lệnh kiểm toàn vẹn gói, rồi chạy:

1. `ai_v5`: 1.896 vector qua thanh ghi Wishbone, scores int16 có dấu, byte
   enables, START khi busy và ABORT — đã PASS.
2. `ai_cpu`: firmware C thực chạy trên PicoRV32, POST 37 trường hợp, trong
   đó 36 gọi AI, một cửa sổ rỗng không gọi — đã PASS. Cửa sổ 1–7 gói vẫn hợp lệ.
3. `features`: năm cửa sổ header kiểm bộ đếm tham chiếu của người 1, gồm SYN,
   SYN-ACK, UDP/ICMP, chiều, đích, phân mảnh và bão hòa cardinality — đã PASS.

Log mới được ghi vào `sim/out/`; log đã đo khi chuẩn bị gói nằm riêng trong
`verification/recorded/`. 84 chu kỳ là trong core; wrapper đo 86 chu kỳ.
Đây không phải tổng thời gian trích đặc trưng/chặn gói trên bo.

## Những gì đã đổi từ ZIP người 1

- `sources.f` dùng `rtl/part2_ai/ai_core_model_v5.v` thay core V2.
- `fw/main.c` dùng `ai_v5_prepare_window()`, in phiên bản/hash V5 và kiểm
  37 tham chiếu mới. POST bỏ gọi AI cho hàng rỗng.
- `fw/part2/` và `fw/ai_vectors.h` dùng đúng header/vector V5.
- Đã build lại `fw/firmware.hex` và `fw/firmware_sim.hex`; image cũ không được
  dùng với core mới. Code + data + BSS khoảng 12,9 KB trong RAM 16 KB; phần còn
  lại dành cho stack, chưa đo đỉnh stack trên bo.
- Testbench demo đợi POST xong mới nhấn nút. Xung nhấn được kéo đủ lâu để
  CPU có thể đọc trong lúc in UART; mức tải, gói, nhãn, model và policy giữ nguyên.
- Runner trả lỗi khi testbench in FAIL, kể cả khi `$finish` trả exit code 0.
- Vector generator kiểm hash model để tránh sinh lại bảng V2 cho firmware V5.

`wb_ai_regs.v` giữ nguyên map `AI_BASE=0x30000000` và cách chốt kết quả.
Model/RTL V2 gốc được giữ trong ZIP tham khảo `reference/original_v2_ai.zip`;
không thêm ZIP tham khảo vào source active. File `.fs` build sẵn của bản cũ
được loại khỏi bản V5 để tránh nhầm firmware/core khi nạp.

## Kết quả toàn hệ thống cần đọc

```bash
cd ~/Downloads/ghep_phan1_ai_v5
sh run_sim.sh full
```

Đã chạy hết 40 giây mô phỏng với traffic demo gốc:

- CPU POST đạt; 37 cửa sổ raw → C pack → bus → scores RTL khớp Python V5.
- 266 khung cảm biến qua, 0 khung cảm biến bị bỏ; ARP/khung trả lời không bị bỏ.
- Scan `.51`: chặn 738 khung và có gỡ chặn; giới hạn SYN lớp 2 bỏ 775 khung giả IP.
- Đợt SYN `.50` khoảng 400 gói/cửa sổ: V5 dự đoán Normal, không chặn; full
  test vẫn FAIL (hai kiểm tra phụ thuộc lần chặn SYN đó). Không đổi luật
  ngưỡng thành đường chặn thay cho AI để làm bài này PASS.
- Trace ví dụ: raw `[407,40,125,2,1,1]`, q `[50,20,125,2,1,1]`, scores
  `[416,96,-541]` → Normal. Python và RTL cùng kết quả này.

```bash
sh run_sim.sh system
```

Đã thử đường RMII/MAC → parser → feature → CPU → AI bằng testbench của người
1. POST/CPU và chuyển khung cảm biến đạt; kiểm chặn `.50` vẫn FAIL. Test này
còn ghi overflow MAC; cần kiểm riêng prototype MAC của người 1, chưa kết
luận hiệu quả trên đường Ethernet thật. Các testbench khác (OLED/board/MAC
riêng) được giữ để nhóm chạy; không kế thừa kết quả PASS V2 thành kết quả V5.

## Mở top trên Gowin Windows

Tải cùng ZIP trên Windows và giải nén riêng. Trong thư mục gốc của gói, chạy:

```text
python CHUAN_BI_GOWIN.py
```

Lệnh tạo `gateway_phan1_v5.gprj` và wrapper có đường dẫn tuyệt đối tới đúng
`firmware.hex` trên máy đó. Mở project này trong Gowin, chọn top `gowin_top`,
chạy Synthesize và kiểm tài nguyên/cảnh báo. Chưa chạy synthesis/timing cho
toàn top V5 tại đây; số tài nguyên của core V5 riêng không đại diện cả SoC.

Mặc định dùng prototype MAC (`SELFTEST=2`). `--mode demo` dùng traffic stub,
`--mode noeth` để Ethernet nghỉ. Clock hệ thống 27 MHz; hai RMII REF_CLK là
50 MHz, có constraints bất đồng bộ trong `board/tangnano9k.sdc`. Cần kiểm
place-and-route của top và nối dây thực tế trước khi xác nhận trên bo.

## Phần còn thiếu để hoàn thiện

Trong ZIP này, `rtl/stubs/pkt_parser_stub.v`, `feat_core_stub.v` và
`pkt_filter_stub.v` là bản tham chiếu do người 1 viết. Chúng có logic hoạt
động để mô phỏng, vẫn cần đối chiếu với bản chính thức của người 3. Parser
tham chiếu có thể phát header trước cuối frame, nên phép kiểm chiều dài IP
đầy đủ/truncation cần được làm rõ khi ghép Phần 3 thực tế. Bộ đếm distinct
tham chiếu lưu tối đa 128 giá trị, tương thích clip q=127 nhưng không phải
báo cáo raw cardinality không giới hạn.

IP được bảo vệ/whitelist giữ theo `fw/config.h` của người 1 (`192.168.10.2/32`).
Lab namespace MQTT trước đây dùng `198.18.0.1`; cần cấu hình khớp đích lab
thực tế khi nối hệ thống. Model không nhận số IP làm đầu vào. Các policy
hai cửa sổ, whitelist, xác nhận nguồn và TTL của người 1 được giữ nguyên.

Số học ghép đúng không sửa được lỗi phân loại SYN đã thấy. Bản này dùng để
kiểm ghép và chẩn đoán; chưa xác nhận chất lượng phát hiện độc lập, timing
toàn top hoặc chạy/chặn Ethernet trên Tang Nano 9K. Muốn nâng chất lượng
model tiếp cần một ứng viên riêng và quy trình đánh giá rõ, giữ V5 làm đối chứng.

## Build lại firmware (khi thực sự sửa code/config)

```bash
cd fw
sh build_fw.sh
```

Cần compiler RV32I và libgcc như bản của người 1. Các image trong gói đã
được build và chạy CPU mô phỏng. Sau khi sửa, hash gói cũ không còn khớp;
chạy từng `sh run_sim.sh ai_v5`, `ai_cpu`, `features`, rồi full/system và
ghi lại kết quả cho bản mới. Không dùng log cũ để xác nhận firmware mới.

Giấy phép PicoRV32/font và tài liệu gốc của người 1 được giữ trong gói.
