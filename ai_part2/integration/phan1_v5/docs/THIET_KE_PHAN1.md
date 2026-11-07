> Tài liệu gốc Phần 1 cho V2. Các kết quả PASS và vector V2 dưới đây là lịch sử; xem README.md và MO_KET_QUA_GHEP_V5.html cho bản V5.

# Thiết kế và kết quả Phần 1 – CPU, bus, firmware, tích hợp

## 1. Công việc đã làm

**CPU và bus**
- Ghép PicoRV32 RV32I với bus Wishbone 32 bit, giải mã 6 vùng địa chỉ theo 4 bit cao.
- Bus đọc ghép bằng cổng OR: mọi slave trả 0 khi không được đọc, nên khỏi cần bộ chọn 6 đường.
- RAM 16 KB trong BSRAM chứa firmware, nạp sẵn từ `firmware.hex` lúc build.
- Tắt `CATCH_MISALIGN`, vì gcc rv32i luôn truy cập thẳng hàng; tiết kiệm ô logic.

**Các khối thanh ghi**
- `wb_uart`: UART TX 115200 cho log.
- `wb_feat_regs`: đọc 6 đặc trưng, IP nghi vấn, `CONFIRM_CNT`; cờ READY/OVERRUN; thêm `PROT_NET`/`PROT_MASK` để chỉ đếm gói đi vào máy cần bảo vệ.
- `wb_ai_regs`: nạp đặc trưng, START/ABORT, đọc lớp, 3 điểm, số chu kỳ AI chạy.
- `wb_sys`:
  - nút S1;
  - bộ đếm chu kỳ;
  - I2C bit-bang cho OLED;
  - thanh ghi ID và nháp để tự kiểm tra;
  - đo tần số REF_CLK của 2 LAN8720 (`clk_meter`);
  - `SEC_CYCLES`.
- `wb_filter_regs`: bật/tắt danh sách chặn và giới hạn SYN, 8 ô IP chặn, 5 bộ đếm gói.

**Firmware C (~11 KB)**
- POST lúc khởi động:
  - đọc ghi bus;
  - chạy 7 vector tích hợp qua AI và so đáp án;
  - đo REF_CLK.
- Chính sách mỗi cửa sổ 1 giây:
  1. bỏ qua cửa sổ rỗng;
  2. chạy AI;
  3. kiểm tra hợp lý;
  4. đợi 2 cửa sổ liên tiếp;
  5. IP nghi vấn phải chiếm hơn nửa SYN;
  6. kiểm danh sách trắng;
  7. chặn, tự gỡ sau 60 giây.
- Luật ngưỡng chạy song song để so sánh, chỉ ghi log.
- Log UART có checksum: `$IDS` (17 trường), `$BLK`, `$UNB`, `$CNT`, `$MODE`, `$SYN`.
- Nút S1: nhấn ngắn đổi DETECT/BLOCK; giữ ≥ 2 giây bật/tắt giới hạn SYN. Đo thời gian giữ lúc nhả nút, để không nhận nhầm khi CPU đang bận.
- Driver OLED SSD1306:
  - bộ đệm chữ 8×21 thay cho bộ đệm ảnh 1 KB;
  - vẽ xoay vòng từng dòng, không chặn việc xử lý cửa sổ;
  - không có màn thì vẫn chạy.
- Mọi thông số chính sách gom vào `fw/config.h`.

**Top của kit và build**
- `tangnano9k_top.v` có các tham số `SELFTEST` (0/1/2), `REF_METER`, `SEC_CYCLES`, `BAUD`, `DEBOUNCE_CYC`.
- Gán chân cho 2 module LAN8720 và OLED (16 dây tín hiệu); ràng buộc 3 clock (27 MHz và 2 × 50 MHz).
- Script build Gowin (`gowin_build.tcl`) và Yosys/nextpnr (`build_oss.sh`); file nạp bản kiểm tra nối dây build sẵn.

**Ghép thử end-to-end**
- Khối giả Phần 3 (`pkt_parser`, `feat_core`, `pkt_filter`) đúng cổng như tài liệu nhóm.
- `eth_stub` tự sinh lưu lượng demo.
- MAC Ethernet RMII 2 cổng (`rtl/part4_eth/`) để chạy thử với khung thật (mục 6).

**Kiểm thử**
- 5 testbench; mô hình SSD1306 đọc lại chữ trên màn.
- Script ModelSim (`modelsim_demo.do`) và Icarus (`run_sim.sh/.bat`).
- `check_log.py` kiểm log UART, dùng được cả cho log chụp từ kit.
- Hướng dẫn demo `docs/HUONG_DAN_DEMO.md`.

## 2. Bản đồ thanh ghi

R = đọc, W = ghi. Mọi thanh ghi ghi 32 bit một lần.

### 0x1000_0000 – UART

| Offset | Tên | Ý nghĩa |
|---|---|---|
| 0x00 | DATA | W: gửi 1 byte |
| 0x04 | STATUS | R: bit0 = đang bận gửi |

### 0x2000_0000 – Đặc trưng (Phần 3)

| Offset | Tên | Ý nghĩa |
|---|---|---|
| 0x00 | STATUS | bit0 READY, bit1 OVERRUN |
| 0x04 | CTRL | bit0 ACK, bit1 xóa OVERRUN, bit8 bật khối |
| 0x08 | WIN_ID | Số thứ tự cửa sổ |
| 0x0C | PKT_CNT | Số gói |
| 0x10 | BYTE_SUM | Tổng IPv4 Total Length |
| 0x14 | SYN_CNT | Số gói SYN=1, ACK=0 |
| 0x18 | SRC_IP | Số IP nguồn khác nhau |
| 0x1C | DST_IP | Số IP đích khác nhau |
| 0x20 | DST_PORT | Số cổng đích khác nhau |
| 0x24 | ERR_CNT | Số gói bị loại khỏi thống kê |
| 0x28 | SUSPECT_IP | IP nghi vấn (chọn ở cửa sổ trước) |
| 0x2C | CONFIRM_CNT | SYN của đúng IP nghi vấn trong cửa sổ này |
| 0x30 / 0x34 | PROT_NET / PROT_MASK | Vùng cần bảo vệ |

Yêu cầu với Phần 3: `feat_core` giữ nguyên mọi đầu ra từ `win_valid` này tới `win_valid` kế tiếp, vì khối thanh ghi đọc thẳng, không chốt lại.

### 0x3000_0000 – AI (Phần 2)

| Offset | Tên | Ý nghĩa |
|---|---|---|
| 0x00 | STATUS | bit0 BUSY, bit1 DONE |
| 0x04 | CTRL | bit0 START, bit1 ABORT |
| 0x08 / 0x0C | FEAT_LO / FEAT_HI | 6 đặc trưng 8 bit (q0..q3 / q4..q5) |
| 0x10 | RESULT | 0 bình thường, 1 SYN flood, 2 quét cổng |
| 0x14–0x1C | SCORE0..2 | Điểm 3 lớp (int16 có dấu) |
| 0x20 | LAT | Số chu kỳ của lần chạy vừa rồi |

### 0x4000_0000 – Hệ thống

| Offset | Tên | Ý nghĩa |
|---|---|---|
| 0x04 | CYCLE | Bộ đếm chu kỳ clock |
| 0x08 | OLED_I2C | W: bit0 kéo SCL, bit1 kéo SDA. R: bit8 SCL, bit9 SDA |
| 0x0C | BTN | bit0 = đang nhấn S1 |
| 0x10 | ID | 0x52563332 ("RV32") |
| 0x14 | SCRATCH | Thanh ghi nháp |
| 0x18 / 0x1C | REFA_HZ / REFB_HZ | Tần số REF_CLK đo được |
| 0x20 | SEC_CYCLES | Số chu kỳ của 1 giây |

### 0x5000_0000 – Bộ lọc (Phần 3)

| Offset | Tên | Ý nghĩa |
|---|---|---|
| 0x00 | CTRL | bit0 bật danh sách chặn, bit1 bật giới hạn SYN |
| 0x04 | SYN_LIMIT | Số SYN tối đa mỗi giây |
| 0x08 | BL_VALID | bit i = ô i đang dùng |
| 0x10–0x2C | BL_IP0..7 | IP bị chặn, **chỉ ghi** (đọc ra 0; firmware tự giữ bản sao) |
| 0x40 | CNT_FWD | Số gói cho qua; ghi bất kỳ giá trị nào sẽ xóa cả 5 bộ đếm |
| 0x44 | CNT_DROP_BL | Số gói bị bỏ do danh sách chặn |
| 0x48 | CNT_DROP_SYN | Số gói bị bỏ do giới hạn SYN |
| 0x4C | CNT_CRC_ERR | Số khung lỗi CRC |
| 0x50 | CNT_OVERFLOW | Số khung bị bỏ do đầy bộ đệm |

## 3. Quyết định thiết kế

- **Chỉ đếm gói vào máy cần bảo vệ** (`PROT_NET`/`PROT_MASK`). Trong cầu nối cùng mạng con, gói broadcast/multicast của laptop (mDNS, SSDP…) không làm sai đặc trưng.
- **Bản ghi header có thêm `hdr_frag`, `hdr_l4`:**
  - Gói phân mảnh không đưa vào thống kê nhưng vẫn phải qua danh sách chặn.
  - Chỉ đọc cờ TCP khi có header TCP thật.
- **`$CNT` lấy hiệu số mỗi giây**, không xóa bộ đếm phần cứng, để không mất gói giữa lúc đọc và lúc xóa.
- **Cửa sổ rỗng thì bỏ qua AI** (dùng `ai_v2_prepare_window()` của Phần 2), đánh dấu bằng bit 3 của `flags`.
- **Kiểm tra hợp lý trước khi chặn:**
  - "quét cổng" phải chạm ≥ 3 cổng;
  - "SYN flood" phải có ≥ 20 SYN;
  - đổi kết quả thì đánh dấu bit 4.

  Đặt về 0 trong `config.h` để tắt.
- **Kiểm REF_CLK:** in một lần sau 2 giây và mỗi khi trạng thái đổi. Dùng ở bước kiểm tra nối dây. Bản nộp có thể tắt bộ đo (`REF_METER = 0`) cho đỡ tài nguyên.
- **Tốc độ CPU:** PicoRV32 không có lệnh nhân/chia, nên xử lý 1 cửa sổ mất ~60–90 nghìn chu kỳ (~3 ms ở 27 MHz). Trên kit thoải mái. Trong mô phỏng, đây là lý do 1 "giây" không ngắn hơn 150 000 chu kỳ.

## 4. Giới hạn đã biết

- Mỗi cửa sổ chỉ có 1 IP nghi vấn. Hai nguồn tấn công cùng lúc thì chỉ chặn được nguồn chiếm đa số.
- Đặc trưng đếm trước bộ lọc, nên IP đã bị chặn mà vẫn tấn công thì tiếp tục được gia hạn. Đây là chủ ý: chỉ gỡ khi tấn công dừng hẳn.
- SYN giả IP không chặn được theo IP; chỉ giới hạn SYN mỗi giây, và giới hạn này cũng hạn chế kết nối mới hợp lệ lúc bị tấn công.
- Ngưỡng kiểm tra hợp lý cố định: quét rất chậm (< 3 cổng/giây) hoặc flood < 20 SYN/giây sẽ không bị chặn.
- Kit là tường lửa trong suốt, không phải router: không định tuyến, không NAT, không DHCP.

## 5. Kết quả mô phỏng (kịch bản 40 giây, `tb_gateway`)

| Hạng mục | Kết quả |
|---|---|
| POST: 7 vector tích hợp qua bus | Khớp 7/7, AI chạy 86 chu kỳ |
| Khung của cảm biến .20 / khung của broker + ARP | Qua 266 / qua 227, **bỏ 0** |
| SYN flood từ .50 | `$BLK` sau ~2,2 giây, bỏ 1 571 khung; `$UNB` 6 giây sau khi dừng (bản mô phỏng) |
| Quét cổng từ .51 | `$BLK ... SCAN`, bỏ 732 khung, rồi tự gỡ |
| SYN giả IP 10.x | Không chặn IP nào (đúng); giới hạn SYN bỏ 803 gói khi bật |
| 22 cửa sổ chỉ có cảm biến | Kết luận bình thường 22/22, không báo động |
| `check_log.py` | PASS: mọi dòng đúng checksum, chặn/gỡ đúng IP, đúng thứ tự |

Các bài khác đều PASS: `tb_oled`, `tb_board`, `tb_eth_mac`, `tb_system_mac`.

## 6. MAC Ethernet để ghép thử (`rtl/part4_eth/`)

Bản MAC tối thiểu để chạy thử cả hệ thống với khung Ethernet thật. Nó giữ đúng cổng `frm_*`/`verdict_*`, nên bản chính thức của Phần 4 thay thẳng vào được.

- `rmii_rx`:
  - nhận RMII 2 bit mỗi nhịp 50 MHz, tìm preamble và SFD;
  - kiểm CRC32 (phần dư 0xDEBB20E3);
  - chọn cạnh lấy mẫu bằng tham số `SAMPLE_NEG`.
- `rmii_tx`: phát 7 × 0x55 + 0xD5, dữ liệu kèm FCS gốc (cầu nối không sửa gói), rồi nghỉ IFG 96 bit.
- `async_fifo`: chuyển dữ liệu giữa clock 50 và 27 MHz bằng con trỏ mã Gray (thiết kế Cummings).
- `eth_mac`:
  - 2 cổng, phục vụ lần lượt (round-robin);
  - lưu khung vào BSRAM rồi chuyển hoặc bỏ theo verdict;
  - chốt verdict ngay từ lúc khung bắt đầu, vì verdict có thể đến trước byte cuối.

**Điểm cần lưu ý khi viết MAC trên Gowin:** bộ đệm khung chỉ được có 1 lệnh ghi và nằm trong khối `always` không có reset bất đồng bộ, đọc ra phải qua thanh ghi. Viết khác đi thì Yosys đặt mảng 2 KB vào LUT, tốn gấp 5 lần chip.

**Giới hạn:**
- xử lý 1 khung mỗi lượt;
- chưa có MDIO (dựa vào LAN8720 tự thương lượng 100 Mbps);
- chiều trong → ngoài cũng chậm thêm 1 khung.

## 7. Tài nguyên FPGA (GW1NR-9, 8 640 ô logic)

| Bản build | Ô logic (LUT4 + ALU) | Ghi chú |
|---|---|---|
| Kiểm tra nối dây (`SELFTEST = 0`) | ~56 % | Build được, ~80 MHz; `board/prebuilt/tangnano9k_noeth.fs` |
| MAC lần đầu, bộ đệm khung thành LUT | 539 % | Không đặt được |
| Bộ đệm khung vào BSRAM | 8 833 (102 %) | Không đặt được |
| + tắt bộ đo REF_CLK (`REF_METER = 0`) | 8 631 (99,9 %) | |
| + `BL_IP` chỉ ghi, `wb_feat_regs` không chốt lại | 8 347 (96,6 %) | |
| + bus đọc dùng OR thay bộ chọn 6 đường | **7 994 (92,5 %)** | LUT4 6 534, ALU 1 460, DFF 4 003, BSRAM 13/26 |

Số đo bằng Yosys + nextpnr. nextpnr chưa đặt được bản 92,5 % (thường cần dưới ~90 %), nên bản đầy đủ build bằng Gowin EDA (`board/gowin_build.tcl`).

Nếu vẫn không vừa, còn các hướng sau:
- so 8 IP chặn lần lượt thay vì song song;
- dùng chung 1 xung "mỗi giây";
- thu nhỏ các bộ đếm;
- chuyển sang Tang Nano 20K.
