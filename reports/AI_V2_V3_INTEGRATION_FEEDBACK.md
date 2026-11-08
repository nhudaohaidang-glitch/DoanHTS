# Kiểm tra phản ánh khi ghép AI v2 và đối chiếu v3

Nguồn phản ánh: ảnh trao đổi do người dùng gửi. Đây là kiểm tra các vector đặc trưng được mô tả, không phải xác minh lại 22 PCAP của người ghép: chưa nhận các PCAP/log đó. Không huấn luyện lại hoặc sửa model đã chốt.

## Kết luận

Phản ánh về v2 có cơ sở và tái lập được bằng model gốc, đúng bước lượng tử hóa, header C và RTL. Không cần giả định người ghép đã đóng gói sai để tái lập các lỗi này. V3 nhận đúng một số phản ví dụ của v2 nhưng vẫn báo SYN flood cho một SYN hợp lệ đơn lẻ. Vì vậy không coi việc gửi v3 thay v2 là đã giải quyết toàn bộ phản ánh.

| Tình huống kiểm tra được dựng rõ ràng | v2 integer | v3 integer |
|---|---|---|
| Cảm biến, raw `[7,61,18,1,1,1]` | Scan — sai trong tình huống cảm biến này | Normal |
| Một SYN hợp lệ, raw `[1,40,127,1,1,1]` | SYN flood — chưa đủ bằng chứng flood | SYN flood — vẫn lỗi |
| ACK-only, IPv4 TotalLength 52, một nguồn/đích/cổng, n=1,7,8,30,100 | Scan — sai trong các đối chứng này | Normal |
| ACK-only như trên, n=1000 | Normal | Normal |
| Quét SYN đến một IP, n cổng khác nhau, không nền, n=3..30, IPv4 TotalLength 40 | Cả 28 đầu vào thành SYN flood — sai loại | Cả 28 đầu vào thành Scan |

Đây là 36 probe đặc trưng dựng để chẩn đoán, không phải dữ liệu IoT-23, không phải PCAP mới, không phải tập huấn luyện hoặc benchmark accuracy. Nhãn mong đợi mô tả các kịch bản đối chứng/quét được chủ động dựng; không suy ra một nhãn an toàn tuyệt đối chỉ từ sáu số của lưu lượng vô danh. Người ghép chưa cung cấp toàn bộ đặc trưng cho SYN/ACK/scan nên kết quả bảng áp dụng đúng các điều kiện đã ghi, chưa thay thế việc xem trace thực tế.

V2 không đáp ứng 35/36 kỳ vọng kịch bản, v3 không đáp ứng 1/36. Không đổi các con số đó thành tuyên bố accuracy mạng thực. V3 vẫn có 5/21 cửa sổ quét chậm trộn MQTT bị bỏ sót trong test v3test01 trước đó; probe quét không nền đúng không xóa bỏ giới hạn đã đo này.

## Kiểm tra preprocessing và số học

Model v2 SHA256: `57da88b7b596766749034a5bdf72a9a21be82189517260176e4d8ecdc4387a07`.

Model v3 SHA256: `e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d`.

Cả hai dùng divisors `[8,2,1,1,1,1]`, chia nguyên rồi clip 0..127 đúng một lần. V2 shift1/shift2=6/1; v3=7/0, không trộn header, ROM hoặc tham số giữa hai bản.

Với raw cảm biến `[7,61,18,1,1,1]`:

```text
q = [0,30,18,1,1,1]
feat[47:0] = 0x010101121e00
v2 scores [Normal,SYN,Scan] = [920,-1834,1005] -> Scan
v3 scores [Normal,SYN,Scan] = [744,-1024,260] -> Normal
```

Nếu đưa thẳng raw `[7,61,18,1,1,1]` vào core như q, v2 lại chọn Normal. Đó là sai preprocessing tình cờ làm mất phản ví dụ; không dùng cách đó để sửa. Không chia hai lần. `ai_v*_pack` nhận số gói, TỔNG IPv4 TotalLength và số SYN mở, không nhận trực tiếp mean hoặc tỷ lệ SYN ở các tham số tương ứng.

Các kiểm chứng thực sự đã chạy:

- C header pack của v2 và v3: mỗi bản khớp Python trên cả 36 probe.
- RTL ROM được sinh bằng mã đáng tin từ frozen v2 và RTL v3 đã chốt: mỗi bản `PASS vectors=36 cycles_min=84 cycles_max=84`.
- Model float v3 chọn cùng lớp với integer ở cả 36 probe, kể cả một SYN bị chọn SYN flood.

RTL PASS nghĩa là phần cứng mô phỏng tính đúng model, bao gồm các dự đoán sai về ý nghĩa. Không phải chứng minh nhận diện đúng tấn công hoặc đã chạy trên FPGA.

## Vì sao một SYN có thể bị gán flood

Với một SYN IPv4 dài 40 byte, một nguồn/đích/cổng:

```text
raw = [1,40,127,1,1,1]
q = [0,20,127,1,1,1]
feat = 0x0101017f1400
v3 scores = [-407,240,184] -> lớp 1
```

Ngay model float cũng chọn lớp 1, nên không thể chữa bằng thay phép nhân hoặc dịch số nguyên. 1..7 SYN với cùng đặc điểm đều có q0=0 và cùng đầu vào q; phép chia số gói cho 8 đã làm mất phân biệt giữa các số lượng nhỏ đó. Tỷ lệ SYN=127 chỉ nói tất cả gói quan sát được là SYN mở, không chứng minh lưu lượng đủ lớn hoặc kéo dài để gọi là flood. Model hiện tại không có trạng thái thời gian liên cửa sổ. Không thể xác định chắc ý đồ của kết nối chỉ từ các đặc trưng này.

`ai_v3_prepare_window()` chỉ bỏ cửa sổ RAW packet_count=0. Nó không có điều kiện chống báo flood cho một SYN. Tuyệt đối không đổi guard sang q0>0 để che lỗi: cách đó loại cả các cửa sổ 1..7 gói hợp lệ, gồm quét chậm.

## Hành động khi bàn giao

1. Giữ v2 làm đối chứng tái lập, không đưa v2 thành nguồn quyết định chặn tự động trong các trường hợp này.
2. Nếu tiếp tục ghép v3, gửi trọn core, header và model đúng phiên bản; ghi rõ lỗi một SYN và 5 cửa sổ quét chậm đã biết. Tách tính đúng số học khỏi chất lượng phân loại.
3. Ghi log trước quyết định chặn: model/version/hash; raw sáu đặc trưng và các bộ đếm packets/sum_ip_bytes/syn_open; q sáu byte; packed feat; ba scores; class_id. Kiểm tra mẫu có hướng ingress, IPv4 TotalLength và cửa sổ một giây đúng contract.
4. CPU không dùng riêng class_id làm bằng chứng đủ để chặn IP. Tiêu chí số lượng/tốc độ, thời gian duy trì, quy kết nguồn và TTL phải được thống nhất và đánh giá riêng. Luật ngưỡng đối chứng đã có packet_threshold=24 cho nhánh SYN và port_threshold=3/syn_ratio_threshold=32 cho scan; dùng để đối chiếu, không âm thầm thêm vào AI rồi gọi kết quả đó là AI thuần.
5. Nếu phát triển ứng viên sau, thu thêm development có cảm biến một nguồn, ACK nhỏ, SYN hợp lệ thưa, scan không nền và có nhiều mức nền, SYN flood thật cùng đối chứng tải hợp lệ. Không huấn luyện bằng 36 vector nhân tạo này. Chốt định nghĩa SYN flood và train/validation trước khi thu test mới. Các nguồn đã xem để chỉnh model không còn là test độc lập cho ứng viên sau.

## Tái lập

Tool `ai_part2/tools/check_edge_cases.py` chỉ đọc model, dựng probe ngoại tuyến và xuất JSON/CSV, vector RTL theo đầu ra model cùng chương trình C kiểm tra đóng gói. Không gửi gói, không đổi trọng số, không sửa luật chặn.

```bash
cd ~/ai_part2
.venv/bin/python tools/check_edge_cases.py \
  --model gowin/hybrid_v3/model --output build/edge_feedback_v3
```

Gói `ai_integration_feedback_check.zip` ở gốc nhánh chứa cả v2 đối chứng và v3 ứng viên, mã kiểm tra cùng kết quả đã ghi. README trong gói hướng dẫn chạy bằng Python của môi trường hiện có, GCC và Icarus.
