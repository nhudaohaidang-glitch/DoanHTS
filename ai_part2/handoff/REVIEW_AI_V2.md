# Kết quả kiểm tra độc lập AI v2

Nguồn: ban_giao_ai_v2.zip người dùng gửi ngày 29/10/2026. Đọc dữ liệu và đối chiếu với code của repository; không chạy các script tải lên. Không có PCAP v2 trong gói, nên chưa độc lập xác minh quá trình thu gói hoặc nhãn từ gói gốc.

Model SHA256: `57da88b7b596766749034a5bdf72a9a21be82189517260176e4d8ecdc4387a07`.

## Kết quả

- ZIP CRC đúng; 32 file dữ liệu/tài liệu/code khớp FILE_SHA256.json, không có file thừa ngoài manifest.
- Model JSON, HEX, FREEZE.json, bản model/metrics tham chiếu trong Gowin và record thu holdout khớp hash. 10 capture holdout không trùng ID/hash development theo metadata và đều sau record thu bộ kiểm tra.
- Verilog ROM nhúng và helper lượng tử C đúng với model khi tái tạo từ code đã review. Testbench tải lên khớp testbench của repo. Các file project/Tcl/SDC được đối chiếu với project tái tạo từ cùng model trước khi đóng gói bản bàn giao.
- Tính lại từ CSV: integer đúng 210/210 cửa sổ của 10 phiên, confusion matrix [[105,0,0],[0,63,0],[0,0,42]], FPR0, macro-F1=1. Baseline cũng đúng 210/210; chưa chứng minh AI tốt hơn luật ngưỡng. Không có bão hòa input hoặc cửa sổ rỗng trong holdout này.
- Một phép tính tham chiếu dạng vòng lặp số nguyên độc lập khớp 424 vector gốc và 210 cửa sổ holdout. Chạy lại Icarus bằng testbench repo: cả core HEX và core ROM nhúng đều PASS634, 84 chu kỳ cố định. Kiểm reset khi đang tính, chốt feat, bỏ start khi busy, done một chu kỳ và giữ score sau done nằm trong bài mô phỏng này.
- Host gcc: helper C và guard khớp 1.010 bộ counters, gồm số nhỏ, biên, bão hòa và ngẫu nhiên. Cross-compile/link RV32I/ILP32 thành công với -lgcc; object cần __udivdi3 vì chia uint64. Đây là kiểm build, không phải chạy firmware trên PicoRV32/bo.
- 49 unittest phần mềm passed, gồm thêm kiểm C cho 0,1,7,8 gói và đóng gói guard. Không có thay đổi trọng số, nhãn, shift hoặc thang lượng tử.

## Thông số v2 đã chốt

| Thông số | Giá trị |
|---|---|
| Kiến trúc | 6–8–3 |
| Divisors đầu vào | [8,2,1,1,1,1] |
| shift1 / shift2 | 6 / 1 |
| hidden_scale / score_scale | 16 / 128 |
| Weight fraction bits | [3,4] |
| Seed đã chọn | 11; ba seed có validation integer macro-F1=1, hòa theo thứ tự |
| Baseline đã chốt | packets>=24, ports>=3, SYN q127>=32 theo thứ tự luật đã định |
| Cận trị tuyệt đối accumulator | Layer1<=18117, layer2<=41663, nằm trong int32 |

Scores là int16 có dấu; không phải xác suất. Luật baseline: nếu ports>=3 và SYNq>=32 thì scan; nếu không, packets>=24 và SYNq>=32 thì SYN; còn lại normal. Không sửa luật theo holdout.

## Điểm bắt buộc khi tích hợp: cửa sổ rỗng

Với feat=000000000000, model cho scores [-1291,-789,2140], class2. Vector này là một phép kiểm số học, không chứng minh có scan khi không có gói. Test holdout có 0 cửa sổ rỗng, nên kết quả 210/210 không đo tình huống idle.

Firmware phải kiểm RAW packet_count trước khi gọi AI. Header ai_v2_integration.h bổ sung ai_v2_prepare_window(...,&feat): trả 0 khi packet_count==0, không START/không tạo luật chặn mới từ mẫu đó; trả 1 khi có gói để gọi driver hiện có. Giá trị trả về là sample-valid, không phải nhãn normal/SYN/scan. Không báo một kết quả normal giả khi skip. TTL/expiry của blacklist và giao dịch AI đã chạy từ trước phải xử lý độc lập.

Không dùng q0==0 làm điều kiện bỏ qua: với divisor8, 1..7 gói cũng có q0=0 nhưng vẫn là cửa sổ hợp lệ và có thể cần phát hiện quét chậm. Giữ nguyên core/weights và vector toàn0 để kiểm tính số học; guard thuộc điều khiển đầu vào.

## Phạm vi bàn giao và công việc còn lại

Bản ai_v2_reviewed_code.zip chứa đúng core/model đã kiểm tra, firmware guard, vector số học, thông số/hướng dẫn và bằng chứng tổng hợp; không cần huấn luyện lại để dùng guard. Gói dành cho ghép code; bộ dữ liệu, record thu, metrics đầy đủ vẫn ở bản ban_giao_ai_v2.zip gốc của người dùng.

Người 1 dùng đúng một ai_core và helper C tương ứng, kiểm driver/timeout và vector qua bus. Người 3 so counters raw/quantized/packed trên cùng header stream, chốt exact/bitmap và mốc cửa sổ. Sau đó mới kiểm chính sách chọn IP, bridge hai chiều/ARP, luật lọc, nguồn bình thường vẫn đi qua, nguồn thử nghiệm bị chặn và counters gói lọt/mất.

Gowin445 logic,246 FF,DSP1,BSRAM0 và synthesis Fmax56.4MHz ở phân tích50MHz vẫn là ảnh người dùng cung cấp. Chưa có vendor report/netlist/bitstream để gắn ảnh với hash project. SDC project ghi27MHz; cần chốt clock và timing sau route khi tích hợp. 84 chu kỳ không bao gồm cửa sổ1giây, xác nhận nhiều cửa sổ, truyền bus hoặc chặn gói. Chưa chứng minh hoạt động trên mạng thực địa/IoT-23, hiệu quả bảo vệ MQTT, throughput Ethernet hoặc độ trễ phát hiện/chặn toàn hệ thống.
