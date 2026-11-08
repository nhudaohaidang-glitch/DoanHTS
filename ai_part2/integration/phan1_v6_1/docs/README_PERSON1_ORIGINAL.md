> Tài liệu gốc đi kèm ZIP người 1. Các kết quả mô phỏng/tài nguyên là của bản trước V5.

# IoT Gateway RISC-V – Phần 1: CPU, bus, firmware, tích hợp

Đồ án nhóm **"IoT Gateway RISC-V với AI phần cứng phát hiện DoS và Port Scan"** trên kit **Tang Nano 9K**
(GW1NR-LV9QN88PC6/I5).

Tang Nano 9K đứng giữa 2 cổng Ethernet, làm **tường lửa trong suốt** (transparent bridge firewall):
- Kit không có IP, chỉ chép nguyên khung giữa 2 cổng.
- Phần cứng xét từng gói. Mỗi giây, CPU RISC-V đưa bản tóm tắt lưu lượng vào khối AI.
- Phát hiện **SYN flood** hoặc **quét cổng** thì báo, hoặc chặn IP nguồn, tùy chế độ.

Repo này là **Phần 1**: CPU PicoRV32, bus Wishbone, các khối thanh ghi, firmware C và phần ghép cả hệ thống,
kèm testbench và script mô phỏng.

## Kiến trúc

```
 LAN8720 (cổng A) ─RMII─┐                                   ┌─RMII─ LAN8720 (cổng B)
                        ▼                                   ▲
                 ┌─────────────── MAC Ethernet (Phần 4) ───────────────┐
                 └──khung byte──► pkt_parser ──header──► feat_core      │
                                     (Phần 3)       │    (6 đặc trưng/giây)
                                                    ▼          │
                          verdict ◄── pkt_filter (danh sách chặn, giới hạn SYN)
                                                    ▲          │
  ┌─────────────────────────── Phần 1 ──────────────┼──────────┼──────────────┐
  │  PicoRV32 RV32I ── Wishbone ──┬─ RAM 16 KB (firmware)       │              │
  │                               ├─ UART 115200 (log) ─────────┼──► laptop    │
  │                               ├─ thanh ghi đặc trưng ◄──────┘              │
  │                               ├─ thanh ghi AI ──► ai_core 6-8-3 (Phần 2)   │
  │                               ├─ hệ thống: nút S1, OLED I2C, đo REF_CLK    │
  │                               └─ thanh ghi bộ lọc ──► pkt_filter           │
  └────────────────────────────────────────────────────────────────────────────┘
```

**Câu chốt:** phần cứng lo tốc độ (xét từng gói trong vài nhịp clock), CPU và AI lo quyết định (mỗi giây một lần).

## Phần 1 gồm những gì

- **Lõi hệ thống** `rtl/gateway_soc.v`:
  - PicoRV32 RV32I.
  - Giải mã địa chỉ theo 4 bit cao, 6 slave Wishbone.
  - Bus đọc ghép bằng cổng OR: slave không được đọc thì trả 0.
- **Các khối thanh ghi** `rtl/wb_*.v`: UART, đặc trưng, AI, hệ thống (nút, bộ đếm chu kỳ, I2C bit-bang cho OLED, đo tần số REF_CLK), bộ lọc.
- **Firmware** `fw/` (C, khoảng 11 KB):
  - POST lúc khởi động;
  - chính sách phát hiện và chặn;
  - log UART có checksum;
  - driver OLED SSD1306;
  - xử lý nút S1.
- **Top của kit** `rtl/board/tangnano9k_top.v`, gán chân `board/tangnano9k.cst`, ràng buộc clock `board/tangnano9k.sdc`, script build Gowin và Yosys/nextpnr.
- **Kiểm thử:**
  - 5 testbench;
  - mô hình màn SSD1306;
  - script ModelSim/Icarus;
  - công cụ kiểm log `tools/check_log.py`.

Các phần khác chỉ có mặt để ghép và mô phỏng:

| Thư mục | Nguồn | Ghi chú |
|---|---|---|
| `rtl/part2_ai/`, `fw/part2/` | Phần 2 (AI) | Giữ nguyên bản của bạn phụ trách, không sửa |
| `rtl/stubs/pkt_*`, `feat_core_stub.v` | Phần 1 viết | Khối giả Phần 3, đúng cổng như tài liệu nhóm, để thử trước khi có bản thật |
| `rtl/stubs/eth_stub.v` | Phần 1 viết | Tự sinh lưu lượng demo (cảm biến, SYN flood, quét cổng, SYN giả IP) |
| `rtl/part4_eth/` | Phần 1 viết để ghép thử | MAC RMII 2 cổng, store-and-forward, để chạy thử end-to-end. Bản chính thức theo phân công Phần 4 |

## Firmware làm gì mỗi giây

1. Đợi `win_valid`, đọc 6 đặc trưng, IP nghi vấn và số SYN của IP đó.
2. Cửa sổ rỗng thì bỏ qua AI. Ngược lại, đóng gói đặc trưng, chạy AI (86 chu kỳ đo qua bus) rồi đọc lớp và điểm.
3. **Kiểm tra hợp lý:** "quét cổng" phải chạm ≥ 3 cổng đích; "SYN flood" phải có ≥ 20 SYN.
4. Đủ **2 cửa sổ tấn công liên tiếp** thì mới báo động.
5. Chỉ chặn khi:
   - IP nghi vấn chiếm **hơn nửa** số SYN;
   - IP đó không nằm trong **danh sách trắng**;
   - đang ở chế độ **BLOCK**.

   IP bị chặn được ghi vào 1 trong 8 ô của bộ lọc, **tự gỡ sau 60 giây**.
6. Luật ngưỡng chạy song song, chỉ ghi log để so sánh với AI.
7. Mỗi giây còn in bộ đếm gói (`$CNT`), giảm hạn chặn và vẽ lại OLED.

**Nút S1:** nhấn ngắn để đổi DETECT ↔ BLOCK; giữ ≥ 2 giây để bật/tắt giới hạn 200 SYN/giây. **S2:** reset.

## Bản đồ địa chỉ

| Địa chỉ | Khối | File |
|---|---|---|
| `0x0000_0000` | RAM 16 KB (firmware, stack) | `wb_ram.v`, `fw_ram.v` |
| `0x1000_0000` | UART TX | `wb_uart.v` |
| `0x2000_0000` | Đặc trưng (Phần 3) | `wb_feat_regs.v` |
| `0x3000_0000` | AI (Phần 2) | `wb_ai_regs.v` |
| `0x4000_0000` | Hệ thống | `wb_sys.v`, `clk_meter.v` |
| `0x5000_0000` | Bộ lọc (Phần 3) | `wb_filter_regs.v` |

Chi tiết từng thanh ghi nằm trong `fw/hw.h` và `docs/THIET_KE_PHAN1.md`.

## Chạy mô phỏng

**ModelSim / Questa:** `File > Change Directory` tới thư mục gốc repo, rồi gõ ở Transcript:

```
do sim/modelsim_demo.do quick    # 9 giây đầu, có dạng sóng (sau đó gõ xem_chan, xem_ai, xem_khung)
do sim/modelsim_demo.do full     # toàn kịch bản 40 giây + kiểm log bằng Python (lâu)
do sim/modelsim_demo.do oled     # màn OLED (lâu)
do sim/modelsim_demo.do board    # top của kit với firmware thật
do sim/modelsim_demo.do mac      # riêng MAC Ethernet, có dạng sóng
do sim/modelsim_demo.do system   # toàn hệ thống với MAC thật, có dạng sóng
```

**Icarus Verilog:** `./run_sim.sh <quick|vcd|oled|board|mac|system|all>` (Windows: `run_sim.bat`).

Python 3 chỉ cần cho bước kiểm log. Hướng dẫn demo đầy đủ, kèm cách đọc log và câu hỏi hay gặp: `docs/HUONG_DAN_DEMO.md`.

Bản mô phỏng rút ngắn thời gian:
- 1 "giây" = 150 000 chu kỳ thay vì 27 triệu;
- hạn chặn 6 giây thay vì 60;
- UART nhanh hơn.

Firmware tự đọc độ dài giây từ thanh ghi `SEC_CYCLES`, nên logic giữ nguyên.

## Firmware và file nạp

```
cd fw && ./build_fw.sh         # cần riscv64-unknown-elf-gcc; sinh firmware.hex (kit) và firmware_sim.hex (mô phỏng)
./board/build_oss.sh noeth     # bản kiểm tra nối dây bằng Yosys + nextpnr
gw_sh board\gowin_build.tcl    # bản đầy đủ bằng Gowin EDA (selftest 2 = MAC thật)
```

- `board/prebuilt/tangnano9k_noeth.fs` là bản kiểm tra nối dây đã build sẵn: Ethernet để nghỉ; vẫn chạy POST, OLED, log và đo REF_CLK của 2 LAN8720.
- Tham số `SELFTEST` của top chọn nguồn khung:
  - 2: MAC thật;
  - 1: `eth_stub` tự sinh lưu lượng demo;
  - 0: bản kiểm tra nối dây.

## Log UART (115200 8N1)

```
$IDS,win,cls,alert,pkt,avg,syn%,src,dst,port,flags,lat,base,s0,s1,s2,susp,conf*CS
$BLK,ip,DOS|SCAN,han_giay    $UNB,ip    $CNT,fwd,drop_bl,drop_syn,crc_err,overflow
$MODE,DETECT|BLOCK           $SYN,ON,200 | $SYN,OFF          # ... = ghi chú
```

`CS` là XOR mọi byte giữa `$` và `*`, viết bằng 2 chữ số hex. Các bit của `flags`:

| Bit | Nghĩa |
|---|---|
| 0 | Mất cửa sổ |
| 1 | AI quá thời gian |
| 2 | Có gói bị loại khỏi thống kê |
| 3 | Cửa sổ rỗng, không gọi AI |
| 4 | Kiểm tra hợp lý đã đổi kết quả AI |
| 5 | IP nghi vấn thuộc danh sách trắng |
| 6 | IP nghi vấn không chiếm quá nửa số SYN (thường là SYN giả IP) |
| 7 | Danh sách chặn đầy |

## Màn OLED (SSD1306 0,96", I2C)

```
IDS GW        [CHAN]
Cua so 7: DoS!
AI:DoS  Luat:DoS
Qua : 8 goi/s
Bo  : 400 goi/s
Chan: 192.168.10.50
      con 5 s
AI  : 86 chu ky
```

## Thông số trong `fw/config.h`

| Thông số | Mặc định | Ý nghĩa |
|---|---|---|
| `PROT_NET` / `PROT_MASK` | 192.168.10.2 / 32 | Máy cần bảo vệ (broker MQTT) |
| `ALLOW_LIST` | .2, .20 | Không bao giờ chặn (broker, máy ảo cảm biến) |
| `BLOCK_TTL_S` | 60 | Hạn chặn (giây) |
| `ALERT_ON_N` | 2 | Số cửa sổ tấn công liên tiếp |
| `SCAN_MIN_PORTS` / `DOS_MIN_SYN` | 3 / 20 | Kiểm tra hợp lý (0 = tắt) |
| `SYN_LIMIT_PER_S` | 200 | Giới hạn SYN mỗi giây |
| `MODE_ON_BOOT` | 0 | 0 = DETECT, 1 = BLOCK |
| `OLED_ADDR` / `OLED_COL_OFFSET` | 0x3C / 0 | Đặt offset 2 nếu màn là SH1106 |

## Kết quả

| Testbench | Kiểm tra gì | Kết quả |
|---|---|---|
| `tb_gateway` | Kịch bản 40 giây: cảm biến, SYN flood, quét cổng, SYN giả IP, nút S1 | PASS. Khung của cảm biến: 266 qua, 0 bị bỏ. `check_log.py`: PASS |
| `tb_oled` | Đọc lại chữ trên màn từ mô hình SSD1306 | PASS |
| `tb_board` | Top của kit với `firmware.hex` thật | PASS |
| `tb_eth_mac` | MAC chuyển khung A↔B đúng từng byte; CRC sai hoặc verdict bỏ thì không ra | PASS |
| `tb_system_mac` | Khung Ethernet thật qua MAC → phát hiện → `$BLK` | PASS |

**Tài nguyên** (Yosys, bản đầy đủ có MAC thật): LUT4 6 534 + ALU 1 460 = 7 994 ô logic (≈ 92 %), DFF 4 003, BSRAM 13/26.
Bản kiểm tra nối dây đạt khoảng 80 MHz, so với yêu cầu 27 MHz. Bản đầy đủ đang được build thử bằng Gowin EDA. Chi tiết và các bước đã tối ưu xem `docs/THIET_KE_PHAN1.md`.

## Giấy phép mã bên thứ ba

- `rtl/picorv32.v`: PicoRV32 của Claire Xenia Wolf, giấy phép ISC (`rtl/picorv32_LICENSE.txt`).
- `fw/font5x7.c`, `tools/vendor/glcdfont.c`: font của Adafruit GFX, giấy phép BSD (file `*_LICENSE.txt` đi kèm).
- `rtl/part2_ai/`, `fw/part2/`: thuộc Phần 2 của nhóm.
