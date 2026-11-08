> Tài liệu gốc Phần 1 cho V2. Các kết quả PASS và vector V2 dưới đây là lịch sử; xem README.md và MO_KET_QUA_GHEP_V5.html cho bản V5.

# Hướng dẫn demo Phần 1 – chạy gì, chỉ vào đâu, nói gì

Tất cả demo là **mô phỏng trong ModelSim**, chưa cần kit. (Có Icarus thì dùng `run_sim.bat <tên>` cũng được, cùng kết quả.) Thời gian trong mô phỏng được rút ngắn:
1 "giây" = 150 000 nhịp clock (kit thật là 27 triệu), hạn chặn 6 giây (kit thật 60 giây).

## 0. Chuẩn bị (làm 1 lần)

- **ModelSim** (bản Intel FPGA Starter hoặc Questa đều được) – đã có.
- **Python 3** (không bắt buộc): chỉ để tự kiểm log ở demo `full`. Cài từ python.org, tick "Add to PATH".

Giải nén zip. Mở ModelSim → `File > Change Directory` → chọn **thư mục gốc** (chỗ có file `sources.f`).
Mọi lệnh dưới đây gõ ở ô **Transcript** phía dưới cửa sổ ModelSim.

## 1. Thứ tự demo khi thầy kiểm tra (~10 phút)

> Mẹo: `full` và `oled` chạy lâu, **chạy sẵn trước giờ kiểm tra** rồi để nguyên cửa sổ, lúc demo chỉ cuộn Transcript.
> Lần đầu mỗi lệnh mất thêm ~1 phút để biên dịch.

| # | Gõ ở Transcript | Cho thầy thấy |
|---|---|---|
| 1 | `do sim/modelsim_demo.do quick` | Khởi động, tự kiểm tra, AI chạy mỗi giây, bị SYN flood → bị chặn. **Có dạng sóng** |
| 2 | `do sim/modelsim_demo.do full` (chạy sẵn) | Toàn kịch bản 40 giây: chặn SYN flood, chặn quét cổng, tự gỡ chặn, không chặn nhầm cảm biến |
| 3 | `do sim/modelsim_demo.do oled` (chạy sẵn) | Nội dung màn OLED đọc lại từ mô phỏng |
| 4 | `do sim/modelsim_demo.do mac` | MAC Ethernet (Phần 4) chuyển khung đúng từng byte, bỏ khung CRC sai. Có dạng sóng |
| 5 | `do sim/modelsim_demo.do system` | Toàn hệ thống với MAC thật: khung Ethernet thật đi vào → bị phát hiện → bị chặn. Có dạng sóng |
| 6 | sau demo 1, gõ `xem_chan`, `xem_ai`, `xem_khung` | Phóng to dạng sóng đúng chỗ CPU chặn IP, AI tính, 1 khung đi qua |

Mỗi bài in kết quả vào Transcript: các dòng `[tb] OK ...` và cuối cùng `[tb] PASS`.
Muốn chạy lại cùng bài: gõ lại đúng lệnh (script tự xóa thư viện cũ và biên dịch lại).

## 2. Demo 1 – `quick`: hệ thống khởi động và làm việc

Kết quả trong Transcript (rút gọn), `[t=...]` là thời điểm (giây mô phỏng):

```
# IDS GW - tuong lua Ethernet, PicoRV32 RV32I, AI v2 6-8-3 (Phan 2)
# POST OK: bus, thanh ghi, AI 7/7 vector, LAT 86 chu ky, OLED KHONG tra loi
$MODE,DETECT*28
$IDS,1,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0.0.0.0,0*55        [t=1.3]  im lang (flags=8: cua so rong)
$MODE,BLOCK*66                                          [t=1.8]  testbench nhan nut S1
$IDS,3,2,0,7,61,14,1,1,1,16,86,0,920,-1834,1005,...     [t=3.7]  chi co cam bien
$IDS,6,1,0,406,40,98,2,1,1,0,86,1,187,1638,-1664,...    [t=6.5]  SYN flood: AI bao lan 1
$BLK,192.168.10.50,DOS,6*28                             [t=7.2]  lan 2 -> CHAN!
$IDS,7,1,1,407,40,98,2,1,1,0,86,1,...,192.168.10.50,400*4F
$CNT,8,401,0,0,0*48                                     [t=9.0]  8 goi qua, 401 goi bi bo
```

(`OLED KHONG tra loi` là bình thường: bài này không gắn mô hình màn hình, demo 3 mới có.)

**Nói gì:**
- "Lúc bật nguồn, CPU tự kiểm tra: đọc ghi bus, chạy 7 bộ số mẫu của bạn Phần 2 qua AI phần cứng,
  khớp cả 7, AI trả lời trong 86 nhịp clock."
- "Dòng cảm biến (cửa sổ 3): flags = 16 nghĩa là bước kiểm tra hợp lý của firmware đã xét lại kết quả AI:
  chỉ có 1 cổng thì không thể là quét cổng, nên kết luận là bình thường."
- "Mỗi giây phần cứng tóm tắt lưu lượng thành 6 con số, CPU đưa vào AI rồi in 1 dòng `$IDS`."
- "Giây 5 bắt đầu SYN flood từ máy .50: cửa sổ 6 AI báo DoS lần 1 (chưa chặn, tránh báo nhầm),
  cửa sổ 7 báo lần 2 → chặn IP .50 ở giây 7,2. Từ đó gói của .50 bị phần cứng bỏ ngay, cảm biến vẫn qua."

### Cách đọc 1 dòng `$IDS`

`$IDS,7,1,1,407,40,98,2,1,1,0,86,1,187,1638,-1664,192.168.10.50,400*4F`

| Trường | Giá trị | Nghĩa |
|---|---|---|
| win | 7 | cửa sổ (giây) thứ 7 |
| cls | 1 | AI nói: 0 bình thường, **1 SYN flood**, 2 quét cổng |
| alert | 1 | kết luận cuối (đã đủ 2 giây liên tiếp) |
| pkt | 407 | 407 gói trong giây này |
| avg | 40 | trung bình 40 byte/gói (gói SYN rất nhỏ) |
| syn% | 98 | 98 % là gói SYN mở kết nối |
| src / dst / port | 2 / 1 / 1 | 2 IP nguồn, 1 IP đích, 1 cổng đích (dồn vào 1883) |
| flags | 0 | không có gì bất thường |
| lat | 86 | AI tính mất 86 nhịp clock |
| base | 1 | luật ngưỡng (để so sánh) cũng nói SYN flood |
| s0, s1, s2 | 187, 1638, −1664 | điểm của 3 lớp, lớp 1 cao nhất → SYN flood |
| susp, conf | 192.168.10.50, 400 | IP gửi nhiều SYN nhất, và 400 gói SYN là của nó → hơn nửa → đúng thủ phạm |

`*4F` ở cuối là checksum để dashboard biết dòng không bị lỗi đường truyền.

## 3. Demo 2 – `full`: toàn kịch bản 40 giây

Cuối Transcript có 2 phần, đều phải ra **PASS** (phần thứ 2 chỉ có nếu máy có Python):

```
[tb] khung cam bien: qua 266, bo 0 | tan cong: qua 2141, bo 3106 | khac: qua 227, bo 0
[tb] OK   khung cam bien (192.168.10.20) khong bao gio bi bo
[tb] OK   SYN flood tu .50 bi chan (danh sach chan)
[tb] OK   quet cong tu .51 bi chan (danh sach chan)
[tb] OK   SYN gia IP bi gioi han khi bat lop 2
...
[tb] PASS
...
   AI=SCAN  ket luan=BT    luat=BT    cong=co  : 22
...
PASS
```

**Kịch bản** (mở `sim/out/uart.log` để chỉ từng dòng):

| Giây | Xảy ra gì | Hệ thống làm gì |
|---|---|---|
| 0–2 | Im lặng | Không gọi AI (cửa sổ rỗng) |
| 2–5 | Cảm biến gửi dữ liệu | Bình thường, không báo động |
| 5–11 | SYN flood từ .50 | `$BLK ...50,DOS` sau ~2 giây |
| 11–19 | Bình thường | `$UNB ...50` khi hết hạn |
| 19–24 | Quét cổng từ .51 | `$BLK ...51,SCAN` |
| 27–31 | SYN flood **giả IP** (IP nguồn ngẫu nhiên) | Không chặn IP nào (không có thủ phạm cố định); bật lớp 2 giới hạn SYN thì bỏ bớt |

**Nói gì:**
- "Khung của cảm biến **không bị bỏ lần nào** trong cả 40 giây – lỗi tệ nhất của tường lửa là tự cắt
  thiết bị thật, nên có danh sách trắng và bước xác nhận."
- "SYN giả IP thì không chặn theo IP được vì mỗi gói một IP khác; lúc đó dùng lớp 2: giới hạn số gói SYN mỗi giây."
- Bảng `AI=... ket luan=... luat=... cong=...` cuối log so sánh kết quả AI, kết luận cuối cùng và luật ngưỡng
  trên từng loại cửa sổ; cột `cong=co` là số cửa sổ mà bước kiểm tra hợp lý của firmware đã đổi kết quả.

## 4. Demo 3 – `oled`: màn hình trên kit

```
+---------------------+
|IDS GW        [CHAN] |      <- che do: CHAN hoac PHAT HIEN
|Cua so 8: DoS!       |      <- ket luan (! = da du 2 giay)
|AI:DoS  Luat:DoS     |      <- AI va luat nguong
|Qua : 8 goi/s        |
|Bo  : 400 goi/s      |
|Chan: 192.168.10.50  |
|      con 5 s        |      <- con bao lau thi tu go
|AI  : 86 chu ky      |
+---------------------+
```

**Nói gì:** "Testbench có mô hình con chip SSD1306: nhận lệnh I2C từ firmware, dựng lại ảnh 128×64,
rồi so từng ô với bảng font để đọc ra chữ. Nên đây đúng là thứ sẽ hiện trên màn thật."

## 5. Demo 4 – `mac`: MAC Ethernet (Phần 4)

```
[tb] OK   khung tu A ra o B du 68 byte (64 + 4 FCS)
[tb] OK   noi dung khung ra o B khop tung byte
[tb] OK   khung CRC sai bi bo, khong ra B
[tb] OK   khung bi verdict bo khong ra B
[tb] OK   khung tu B ra o A du 74 byte
[tb] PASS
```

**Nói gì:** "Module LAN8720 gửi 2 bit mỗi nhịp 50 MHz. MAC ghép thành byte, bỏ phần mở đầu, kiểm CRC32,
chuyển sang miền clock 27 MHz của hệ thống qua FIFO bất đồng bộ (con trỏ mã Gray), giữ cả khung trong
bộ nhớ chờ quyết định, rồi phát nguyên vẹn ra cổng bên kia. Khung CRC sai hoặc bị bộ lọc bỏ thì không ra."
(Phần này mình viết thử để ghép sớm; bản chính thức do bạn phụ trách Phần 4.)

## 6. Demo 5 – `system`: toàn hệ thống với MAC thật

```
$MODE,BLOCK*66
$IDS,3,1,0,26,40,100,...                   <- giay 1 cua dot tan cong
$BLK,192.168.10.50,DOS,6*28                <- giay 2 -> chan
$CNT,1,50,0,0,25*46                        <- 1 goi qua (cam bien), 50 bi bo
[tb] OK   khung cam bien .20 luon duoc chuyen ra cong B
[tb] OK   chan dung 192.168.10.50 sau SYN flood ($BLK)
[tb] PASS
```

**Nói gì:** "Lần này không dùng khối giả nữa: testbench tạo khung Ethernet/IPv4/TCP thật, có CRC,
gửi từng 2 bit vào chân RMII như module LAN8720 thật. Toàn bộ đường đi từ chân vào → MAC → tách header
→ đếm → AI → CPU → bộ lọc → MAC → chân ra đều chạy đúng."

Cột cuối `$CNT` = 25: MAC xử lý 1 khung mỗi lượt nên khi bị flood thì bỏ bớt khung mới – đúng thiết kế.

## 7. Demo 6 – xem dạng sóng (sau demo 1)

Sau khi `quick` chạy xong, cửa sổ Wave đã có sẵn tín hiệu. Gõ ở Transcript:
- `xem_chan`: `bl_valid` từ 0 lên 1 (CPU vừa ghi IP .50 vào danh sách chặn), ngay sau đó gói tiếp theo
  của .50 có `verdict_drop = 1` → phần cứng bỏ gói.
- `xem_ai`: `ai_start` → 84 nhịp → `ai_done`, `ai_class = 1` (SYN flood).
- `xem_khung`: từng byte của 1 khung đi qua `frm_data`; `hdr_valid` bật khi đọc xong header.
- `xem_uart`: 1 byte log trên chân `uart_txd`.
- `xem_het`: cả 9 giây.

Ở demo `mac` và `system`, dạng sóng hiện cả đoạn; kéo chuột chọn vùng rồi bấm phóng to để xem 1 khung.

## 8. Giải thích đồ án theo dạng hỏi – đáp

Đọc từ trên xuống là hiểu cả đồ án; lúc bảo vệ thì tra đúng nhóm câu hỏi.

### 8.1 Tổng quan

| Hỏi | Trả lời ngắn |
|---|---|
| Đồ án làm gì? | Tang Nano 9K đứng giữa dây mạng nối vùng ngoài với vùng trong. Mọi gói đều đi qua kit. Phần cứng xét từng gói, AI xét bản tóm tắt mỗi giây. Thấy SYN flood hoặc quét cổng thì báo (chế độ DETECT) hoặc chặn IP nguồn (chế độ BLOCK), còn máy được bảo vệ vẫn chạy bình thường. |
| "Tường lửa trong suốt" nghĩa là gì? | Kit không có địa chỉ IP, không định tuyến, chỉ chép nguyên khung từ cổng A sang cổng B và ngược lại. Cắm vào giữa không phải đổi cấu hình máy nào. |
| Hệ thống chia mấy phần? | 4 phần. **P1**: CPU RISC-V, bus, firmware, ghép hệ thống. **P2**: khối AI. **P3**: đọc header, đếm đặc trưng, bộ lọc. **P4**: MAC Ethernet (RMII) và bộ đệm khung. |
| Sao dùng FPGA mà không dùng máy tính hay vi điều khiển? | Phần cứng xét gói song song, độ trễ cố định vài nhịp clock, không phụ thuộc hệ điều hành. Đó cũng là mục tiêu của môn thiết kế hệ thống số. |
| Sao chọn RISC-V PicoRV32? | Mã nguồn mở, nhỏ (vừa FPGA 9K ô logic), có sẵn giao tiếp Wishbone, viết firmware bằng C với GCC. |
| Sao không để CPU xét từng gói? | 100 Mbps có thể tới hơn 100 nghìn gói/giây; CPU nhỏ không kịp. Phần cứng xét từng gói, CPU chỉ xét bản tóm tắt mỗi giây và sửa luật cho phần cứng. |

### 8.2 Đường đi của một gói

| Hỏi | Trả lời ngắn |
|---|---|
| Một gói đi qua kit thế nào? | (1) LAN8720 gửi 2 bit mỗi nhịp 50 MHz qua RMII. (2) MAC (P4) ghép thành byte, kiểm CRC, đưa sang miền 27 MHz và chép vào bộ đệm. (3) P3 đọc header (IP nguồn/đích, cổng, cờ TCP), cộng vào bộ đếm, so IP với danh sách chặn rồi trả lời "cho qua" hay "bỏ". (4) MAC gửi khung ra cổng kia hoặc bỏ cả khung. |
| Sao phải lưu cả khung rồi mới gửi? | Phải đọc xong header mới biết cho qua hay không, và phải đọc hết khung mới biết CRC đúng hay sai. Lưu trong BSRAM rồi mới gửi thì bỏ được trọn khung xấu. Đổi lại, mỗi khung chậm thêm đúng thời gian nhận nó (khung dài nhất khoảng 0,12 ms). |
| Chiều từ trong ra ngoài có bị lọc không? | Không. Luôn cho qua (vẫn đếm), vì tấn công giả định đến từ vùng ngoài. |
| Sao cần FIFO bất đồng bộ? | PHY chạy 50 MHz, hệ thống chạy 27 MHz, hai clock không cùng pha. FIFO dùng con trỏ mã Gray để chuyển dữ liệu qua mà không đọc sai. |
| Tại sao 27 MHz đủ cho 100 Mbps? | 100 Mbps = 12,5 triệu byte/giây; xử lý 1 byte/nhịp ở 27 MHz là 27 triệu byte/giây, dư gấp đôi. |

### 8.3 Phần 1 – CPU, bus, firmware

| Hỏi | Trả lời ngắn |
|---|---|
| CPU làm gì mỗi giây? | Đọc 6 đặc trưng của giây vừa qua, nạp vào AI, đọc kết quả, áp luật kiểm tra lại, quyết định chặn hay không, ghi IP vào bộ lọc, đếm giờ để tự gỡ chặn, in log UART, vẽ OLED, đọc nút S1. |
| Bus chia địa chỉ thế nào? | Theo 4 bit cao của địa chỉ (Wishbone): 0 = RAM 16 KB, 1 = UART, 2 = đặc trưng (P3), 3 = AI (P2), 4 = hệ thống (nút, OLED, đo clock), 5 = bộ lọc (P3). |
| Firmware nằm ở đâu? | Khoảng 11 KB, nằm trong RAM 16 KB làm bằng BSRAM, được nạp sẵn vào file nạp FPGA lúc build (`firmware.hex`). |
| Lúc khởi động kiểm tra gì? | POST: thử bus và thanh ghi, chạy 7 vector mẫu qua AI và so với đáp án, đo clock 50 MHz của 2 LAN8720. Sai thì OLED hiện "POST LOI" và log ghi chi tiết. |
| Log đi đâu? | UART 115200, mỗi dòng có checksum: `$IDS` (kết quả mỗi giây, 17 trường), `$BLK` (chặn), `$UNB` (gỡ chặn), `$CNT` (bộ đếm gói), `$MODE`, `$SYN`. Laptop trong đọc log và đưa lên dashboard. |
| Nút S1 làm gì? | Nhấn ngắn: đổi DETECT ↔ BLOCK. Giữ ≥ 2 giây: bật/tắt giới hạn số SYN mỗi giây. |

### 8.4 Phần 2 – AI

| Hỏi | Trả lời ngắn |
|---|---|
| AI là mạng gì? | MLP 6-8-3. 6 đầu vào là số liệu của 1 giây: số gói, tổng byte, số SYN, số IP nguồn khác nhau, số IP đích khác nhau, số cổng đích khác nhau. 8 nơ-ron ẩn. 3 đầu ra: bình thường / SYN flood / quét cổng. |
| Chạy trên phần cứng thế nào? | Trọng số 8 bit có dấu nằm trong ROM. Một bộ nhân-cộng dùng chung tính lần lượt từng phép; xong trong 84 nhịp (86 nhịp tính cả bus), khoảng 3 µs. |
| Sao dùng số nguyên 8 bit mà không dùng số thực? | Số thực tốn rất nhiều ô logic. Mô hình được huấn luyện trên máy tính rồi lượng tử hóa về 8 bit; firmware chia đặc trưng theo hệ số cho sẵn để đưa vào AI. |
| Sao cần luật kiểm tra lại sau AI? | Là lớp an toàn trước khi chặn: firmware chỉ chấp nhận "quét cổng" khi có ≥ 3 cổng, "SYN flood" khi có ≥ 20 SYN. Giây bị luật đổi kết quả được đánh dấu bằng bit 4 trong `$IDS`. |
| AI có hơn luật ngưỡng không? | Firmware chạy luật ngưỡng song song, chỉ ghi log để so sánh; báo cáo sẽ so tỉ lệ báo nhầm/bỏ sót của cả hai trên dữ liệu lab. |

### 8.5 Phần 3 – đặc trưng và bộ lọc

| Hỏi | Trả lời ngắn |
|---|---|
| Phần 3 gồm gì? | `pkt_parser` đọc header. `feat_core` đếm 6 đặc trưng mỗi giây và chọn IP nghi vấn. `pkt_filter` so IP nguồn với danh sách chặn (8 ô), giới hạn SYN mỗi giây và trả lời cho qua/bỏ cho từng gói. |
| "Cửa sổ 1 giây" là gì? | Bộ đếm cộng dồn trong 1 giây, hết giây thì chốt số và báo CPU, rồi đếm lại từ 0. CPU đọc số đã chốt trong giây kế tiếp. |
| IP nghi vấn dùng để làm gì? | Giây trước chọn IP gửi nhiều SYN nhất; giây này đếm riêng SYN của đúng IP đó. Chỉ chặn khi IP đó chiếm hơn nửa tổng số SYN, nên không chặn bừa khi nhiều máy cùng gửi. |

### 8.6 Phần 4 – MAC Ethernet

| Hỏi | Trả lời ngắn |
|---|---|
| RMII là gì? | Chuẩn nối chip PHY (LAN8720) với MAC: 2 bit dữ liệu mỗi nhịp clock 50 MHz = 100 Mbps. Ít chân, vừa với số chân của Tang Nano. |
| Kiểm CRC thế nào? | Tính CRC32 suốt khung, kể cả 4 byte FCS ở cuối; khung đúng thì phần dư luôn bằng hằng số 0xDEBB20E3. Sai thì bỏ khung và tăng bộ đếm lỗi. |
| Gửi đi có tính lại CRC không? | Không. Khung không bị sửa nên phát lại nguyên FCS gốc. |
| Hai cổng cùng có khung thì sao? | Phục vụ lần lượt (round-robin), mỗi lần một khung, để không cổng nào bị bỏ đói. |

### 8.7 Chặn và an toàn

| Hỏi | Trả lời ngắn |
|---|---|
| Mất bao lâu mới chặn? | 1–2 giây (đợi đủ 2 giây liên tiếp để tránh báo nhầm). Sau khi chặn thì gói kế tiếp bị bỏ trong vài nhịp clock. |
| Chặn nhầm máy thật thì sao? | 3 lớp an toàn: phải 2 giây liên tiếp, IP phải chiếm hơn nửa số SYN, và không nằm trong danh sách trắng. Tự gỡ sau 60 giây. |
| Danh sách trắng để làm gì? | Các IP quan trọng (.2 = Laptop trong chạy broker, .20 = máy ảo cảm biến) không bao giờ bị chặn. |
| SYN flood giả IP? | Không chặn được theo IP; dùng giới hạn số SYN mỗi giây (giữ S1). Đổi lại, kết nối mới hợp lệ cũng bị hạn chế lúc đang bị tấn công. |

### 8.8 Kiểm thử và giới hạn

| Hỏi | Trả lời ngắn |
|---|---|
| Kiểm tra bằng cách nào? | 5 testbench trong ModelSim. Testbench tự sinh khung của cảm biến, SYN flood, quét cổng, IP giả, rồi tự so kết quả. `check_log.py` kiểm từng dòng `$IDS` đủ 17 trường. |
| Sao mô phỏng 40 giây mà chạy nhanh? | Bản mô phỏng rút ngắn: 1 giây = 150 000 nhịp thay vì 27 triệu, thời gian tự gỡ chặn 6 giây thay vì 60. Logic giữ nguyên, chỉ đổi hằng số. |
| Có chạy trên kit thật chưa? | Chưa. Mô phỏng đủ 5 bài trong ModelSim. Tài nguyên dùng ~92 % FPGA, đang build bằng Gowin để kiểm tra vừa không; đã có file nạp bản kiểm tra nối dây. |
| Giới hạn của đồ án? | Chỉ xét IPv4 và TCP SYN; tốc độ tối đa 100 Mbps; FPGA gần đầy nên khó thêm tính năng; AI còn phụ thuộc luật kiểm tra lại. |

## 9. Build thử bằng Gowin (kiểm tra mạch có vừa kit không)

1. Mở Command Prompt ở thư mục gốc, chạy (sửa đường dẫn theo nơi cài Gowin):
   `"C:\Gowin\Gowin_V1.9.x_x64\IDE\bin\gw_sh.exe" board\gowin_build.tcl`
   Mặc định build **MAC thật, bản gọn** (`selftest 2`, `ref_meter 0` ở đầu file `.tcl`).
2. Mở file báo cáo tài nguyên trong `impl\pnr\` (tên `tangnano9k.rpt.txt` hoặc tương tự), tìm bảng
   **Resource Usage Summary**: dòng `Logic` (LUT + ALU), `Register`, `BSRAM`.
3. Ghi lại 3 dòng đó. Nếu có file `impl\pnr\tangnano9k.fs` là đã vừa và nạp được.
4. Nếu Gowin báo chân trùng chức năng phụ (MSPI/SSPI/JTAG…): vào Project > Configuration >
   Dual-Purpose Pin, tick dòng tương ứng, build lại.
