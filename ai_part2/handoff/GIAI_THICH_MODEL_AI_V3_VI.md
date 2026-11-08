# Hiểu model AI v3: từ gói mạng đến trọng số và kết quả

Tài liệu này giải thích đúng bản v3 có SHA256 `e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d`. Không huấn luyện lại hoặc thay model. V2 mà bạn đã gửi trước đó có trọng số khác và nhiều lỗi được xác nhận trong báo cáo phản ánh ghép nối.

## 1. Model AI của chúng ta là gì?

Đó là một hàm đã được học từ các ví dụ có nhãn: nhận sáu con số mô tả một giây lưu lượng mạng, tính ba điểm số, chọn lớp có điểm lớn nhất. Ba lớp là 0 Normal, 1 SYN flood, 2 TCP vertical scan. Model hiện tại là MLPClassifier của scikit-learn, mạng truyền thẳng fully connected 6–8–3 với một tầng ẩn ReLU.

Kiến trúc là cách bố trí phép tính; trọng số/bias là các số được học; các lựa chọn như solver, số neuron, alpha là siêu tham số; Verilog là cách thực hiện phép tính trên FPGA. Model không phải toàn bộ tường lửa. Nó không đọc chuỗi nhiệt độ MQTT, không biết IP nào phải chặn từ sáu số đếm, không tự ghi luật lọc, không học thêm trong lúc bo chạy.

## 2. Công việc đã làm

1. Dựng lab Ubuntu cô lập với MQTT broker tại198.18.0.1:1883, cảm biến mô phỏng tại198.18.0.2, nguồn thử nghiệm tại198.18.0.3. Nguồn đó tạo kịch bản SYN/scan hoặc đối chứng retry; cảm biến gửi nhiệt độ mô phỏng. Đây không phải phép đo cảm biến vật lý hoặc tấn công Internet.
2. Ghi PCAP, nguồn nhãn/manifest, log MQTT và kiểm tra nguồn thử nghiệm, packet drops, timestamp.
3. Định nghĩa sáu đặc trưng, cửa sổ một giây, nguồn dữ liệu train/validation/test, preprocessing và định dạng giao tiếp.
4. Huấn luyện các bản lab ban đầu và v2; kiểm số nguyên, mô phỏng RTL, tổng hợp Gowin.
5. Thử dữ liệu khác, phát hiện giới hạn của model lab. Người dùng chọn giữ SYN flood/vertical scan và cho phép kết hợp IoT-23 với lab.
6. Kiểm nhãn và TCP flags của IoT-23; chỉ dùng đoạn DDoS đã có bằng chứng SYN-only, không gọi nhãn quét ngang là quét dọc.
7. Huấn luyện/chốt v3 lai IoT-23+lab; giữ v2 đối chứng. Tái kiểm tra Somfy benign dành riêng và test lab mới sau freeze; tái lập lỗi từ PCAP và phản ánh ghép nối.
8. Xuất core Verilog/header/vectors/model. Đã có số tài nguyên tổng hợp v3 riêng. Chưa đo hành động chặn, CPU/bus tích hợp, routed timing, độ trễ toàn hệ thống trên bo.

## 3. Luồng offline và luồng chạy thật

```text
Gói mạng lab hoặc PCAP IoT-23
  -> lọc hướng IPv4 ingress tới IP được bảo vệ
  -> gom cửa sổ đầy đủ một giây
  -> tính sáu đặc trưng nguyên
  -> gắn nhãn và nguồn/split theo kịch bản/nguồn có bằng chứng
  -> CSV + metadata
  -> chia theo nguyên capture, preprocessing
  -> fit trên train, chọn bằng validation
  -> float weights -> integer weights -> freeze
  -> test mới và kiểm RTL
```

```text
Ethernet thực tế -> parser/bộ đếm đặc trưng của nhóm
  -> raw sáu đặc trưng -> chia/clip/pack đúng header
  -> core AI chạy với weights đã chốt
  -> scores + class_id -> CPU/policy và quy kết nguồn
  -> cập nhật bộ lọc nếu đủ điều kiện
```

Model chỉ tham gia đoạn suy luận. Phần mềm huấn luyện chạy trên Ubuntu bằng CPU, không huấn luyện mạng trên Tang Nano9K. Hiện chưa xác minh toàn bộ luồng Ethernet trên bo.

## 4. Dữ liệu được lưu thành những dạng nào?

- `traffic.pcap`: tệp nhị phân gồm các frame bắt được và timestamp. Có thể mở Wireshark; có IP, TCP/UDP, flags, port, chiều trả về, ARP, v.v.
- `manifest.csv`: mỗi dòng là capture hoặc đoạn thời gian được gán nhãn; chứa capture_id, đường dẫn PCAP, split, label, start/end, source_kind và target_net.
- CSV đặc trưng: mỗi dòng là một cửa sổ thời gian. Đây là bảng từ đó tạo X và y.
- `.meta.json`: SHA256 PCAP, quy tắc cửa sổ/đếm, nguồn, thống kê gói bị bỏ/đảo timestamp; phục vụ kiểm toán, không đưa toàn bộ metadata vào AI.
- `sensor.jsonl`, `received.jsonl`: kết quả publish/receive MQTT, nhiệt độ, thời gian thao tác. Dùng kiểm tra dịch vụ; không trực tiếp dùng nhiệt độ, nội dung JSON hoặc thời gian publish làm đầu vào sáu đặc trưng.
- `model.json`: trọng số/bias số nguyên, divisor và shift. Đây là kết quả huấn luyện, không phải bảng lưu lượng.

## 5. Sáu đặc trưng chính xác

Chỉ tính IPv4 hợp lệ chiều ingress tới target_net. Bỏ fragment và truncated IP, ghi thống kê rõ. ARP và chiều trả về không tính vào các đặc trưng này. Dữ liệu phần mềm hiện dùng distinct exact.

| Thứ tự | Tên | Nghĩa/công thức |
|---|---|---|
| f0 | packet_count | Số gói IPv4 hợp lệ trong cửa sổ |
| f1 | mean_ip_bytes | floor(tổng IPv4 TotalLength / số gói) |
| f2 | syn_ratio_q127 | floor(127 × số SYN mở / tất cả gói IPv4 hợp lệ) |
| f3 | src_count | Số IP nguồn khác nhau |
| f4 | dst_count | Số IP đích khác nhau |
| f5 | dst_port_count | Số cổng đích TCP/UDP khác nhau |

SYN mở là SYN=1 ACK=0; SYN-ACK không tính. Mẫu số f2 là tất cả gói ingress hợp lệ, không chỉ TCP hoặc chỉ lưu lượng tấn công. f2=127 nghĩa là 100% gói là SYN mở, không phải127% và không đủ chứng minh flood. Độ dài là IPv4 TotalLength, không phải toàn frame Ethernet hoặc chỉ payload.

Cửa sổ là [T,T+1), chia theo epoch timestamp; chỉ lấy cửa sổ đầy đủ trong khoảng gán nhãn. Cùng một PCAP có thể chứa MQTT bình thường và quét trong một giây: số đếm phản ánh cả hai. Cần căn mốc cửa sổ giữa phần mềm và RTL. RAW packet_count=0 phải skip/report; q0=0 không đồng nghĩa rỗng.

## 6. Ba dòng CSV thực và cách đọc

Trích nguyên đặc trưng từ dữ liệu development đã dùng huấn luyện v3 (các dòng này không phải test độc lập):

```csv
capture_id,split,label,source_kind,window_start,packet_count,mean_ip_bytes,syn_ratio_q127,src_count,dst_count,dst_port_count
challenge01_normal_large,train,0,lab,1793278615.0,16,136,15,1,1,1
challenge01_syn_low,train,1,lab,1793278710.0,29,48,96,2,1,1
challenge01_scan_slow,train,2,lab,1793278773.0,13,58,58,2,1,6
```

X là sáu cột packet_count tới dst_port_count. y là label. capture_id, split, source_kind và window_start phục vụ quản lý/kiểm tra, không đi vào sáu neuron đầu vào. Không cho model đọc nhãn lúc dự đoán.

- Normal:16 gói,136 byte trung bình, tỷ lệ SYN xấp xỉ15/127; một nguồn/đích/cổng. Có SYN hợp lệ khi MQTT kết nối, không yêu cầu tỷ lệ SYN bằng0 để được normal.
- Kịch bản SYN:29 gói,48 byte trung bình, tỷ lệ SYN khoảng 96/127; hai nguồn vì có cả cảm biến và nguồn thử nghiệm, chỉ một cổng đích. Nhãn1 đến từ kịch bản tạo lưu lượng SYN đã ghi nhận; con số đó không tự chứng minh dịch vụ MQTT đã bị từ chối phục vụ.
- Scan:13 gói,58 byte, sáu cổng đích, một IP đích; có cả MQTT nên tỷ lệ SYN không bằng127. Kịch bản và PCAP xác nhận hoạt động quét dọc.

Các dấu hiệu là cơ sở trực giác, không phải luật định nghĩa tuyệt đối. Lưu lượng hợp lệ dùng nhiều cổng cũng có thể giống scan; một SYN có thể có tỷ lệ SYN=100%. Model học tương quan trong dữ liệu, không tự suy luận giao thức như con người.

## 7. Nhãn đến từ đâu?

Trong lab, biết nguồn nào chạy, chạy kiểu gì, khoảng thời gian nào; kiểm source.log/PCAP để chắc có hoạt động đó. Label gắn cho kịch bản/cửa sổ, không nói mọi gói trong cửa sổ là độc hại. Không có nhãn per-packet hoàn hảo tự suy ra từ mỗi TCP flag.

IoT-23 benign dùng nhãn benign của nguồn công bố. Đoạn native SYN ởcapture34 được kiểm TCP flags:40568 SYN-only về71.61.66.148:80, phù hợp luồng gốc Malicious/DDoS, khoảng 22 giây; lấy 21 cửa sổ đầy đủ không rỗng. Không phải mọi DDoS của IoT-23 đều được đổi thành SYN. Vertical scan dùng lab, không đổi PartOfAHorizontalPortScan thành vertical.

## 8. V3 đã học trên bao nhiêu dữ liệu?

| Phần | Nguồn | Số cửa sổ không rỗng |
|---|---|---:|
| Train | Lab challenge01 cũ | 182 |
| Train | IoT-23 Philips Hue4 benign | 2880 |
| Train | IoT-23 native SYN capture34 | 21 |
| Train tổng | 9 capture | 3083 |
| Validation | Lab v2test01 cũ | 210 |
| Validation | IoT-23 Amazon Echo5 benign | 1619 |
| Validation tổng | 11 capture | 1829 |

Tổng development4912 dòng. Train theo lớp2958 normal/73 SYN/52 scan. Validation1724 normal/63 SYN/42 scan. Challenge v1 và holdout v2 cũ đã được chuyển rõ thành development v3, không còn là test độc lập v3. Chia nguyên capture, không trộn ngẫu nhiên các giây liền nhau sang train và test.

Sau lượng tử hóa, train chỉ còn 55 điểm normal khác nhau,27 SYN,25 scan:107 điểm khác nhau tính theo từng lớp. Khi fit, lặp các điểm train để mỗi lớp có 55 dòng, tổng 165 dòng. Không sinh thêm lưu lượng;165 dòng lặp không phải165 capture hoặc ví dụ độc lập. Đánh giá vẫn tính trên toàn bộ cửa sổ gốc. Nhiều giây giống nhau và chỉ một đợt SYN IoT-23 khiến độ đa dạng thực tế thấp hơn số dòng gợi ý.

## 9. Preprocessing và input FPGA

Divisors v3 cố định theo hợp đồng v2: `[8,2,1,1,1,1]`, không học lại từ test. Công thức q_i=min(127,max(0,floor(f_i/divisor_i))).

```text
Normal raw: [16,136,15,1,1,1] -> q=[2,68,15,1,1,1]
SYN raw:    [29,48,96,2,1,1]  -> q=[3,24,96,2,1,1]
Scan raw:   [13,58,58,2,1,6]  -> q=[1,29,58,2,1,6]
```

Mỗi q là một byte nhưng chỉ dùng0..127. q0 ởfeat[7:0], q5 ởfeat[47:40]; normal ví dụ cófeat=0x0101010f4402. Chia/clip đúng một lần. Header C nhận packets, TỔNG ip_bytes, số SYN mở và cardinalities, tự tính mean/ratio; không truyền mean/ratio vào vị trí tổng/số đếm.

Khi fit float, đầu vào x=q/128. Khi chạy integer RTL, đưa q trực tiếp vào core; scale đã được hấp thụ trong weights/bias/shifts. Không chia thêm128 trong firmware.

## 10. Mạng 6–8–3 và 83 tham số

```text
6 đầu vào q -> 8 neuron ẩn ReLU -> 3 scores -> argmax -> class0/1/2
```

| Thành phần học | Kích thước trong model integer | Số tham số |
|---|---:|---:|
| W1: input -> hidden | 8×6 | 48 |
| b1: bias hidden | 8 | 8 |
| W2: hidden -> output | 3×8 | 24 |
| b2: bias output | 3 | 3 |
| Tổng | | 83 |

Weight là hệ số nhân, bias là số cộng thêm của neuron. 6 số đầu vào là dữ liệu, không phải6 tham số được học. 83 là số vị trí tham số của kiến trúc, không phải83 lớp hoặc83đặc trưng. Sau quantization v3 có 17/48W1 và14/24W2 khác0; cả 11 bias khác0. Kiến trúc vẫn có 83 vị trí dù nhiều vị trí bằng0.

Các lựa chọn khác là cấu hình/siêu tham số: window1 giây, hidden 8, solverlbfgs, ReLU, alpha 0.01, seed 11, max_iter1600. Divisor/shift là tham số preprocessing/triển khai, không cộng vào83 tham số học của mạng.

## 11. Huấn luyện thay đổi cái gì?

scikit-learn khởi tạo weights/bias theo seed, tính scores/probabilities cho train, so với y, tính cross-entropy kèm phạt L2, dùng L-BFGS điều chỉnh toàn bộ83 tham số để giảm loss. Alpha0.01 là hệ số L2, không phải learning rate. max_iter1600 là giới hạn vòng lặp bộ tối ưu, không có nghĩa đã chạy đúng 1600 epoch kiểu mini-batch.

Thử9ứng viên: seeds11/23/47 × alpha 0.01/0.1/0.001. Chọn theo integer validation: recall cân bằng theo capture/lớp trước, rồi macro-F1, rồi FPR nguồn xấu nhất, rồi thứ tự cố định. Chọn seed 11/alpha 0.01. Tái lập riêng ứng viên đã chọn hội tụ189 vòng, không warning và cho cùng weights integer. Dữ liệu test không được dùng chọn ứng viên này; nếu sửa model dựa trên kết quả test đã xem thì cần test mới cho ứng viên sau.

## 12. Từ float sang integer

Model float dùng trọng số thực. Để triển khai FPGA, v3 dùng weights int8 có dấu, bias/accumulator int32, q/h0..127, scores int16 có dấu. Chuyển đổi làm tròn và có thể mất thông tin; phải so sánh float/integer, không giả định tương đương trên mọi đầu vào.

V3: weight_fraction_bits=[3,3], hidden_scale=8, score_scale=64, shift1=7, shift2=0. W1/W2 gần với float_weights×8 được làm tròn; b1 gần float_b1×1024, b2 gần float_b2×64. Shift1 chia128 để hidden integer gần8lần hidden float. Score integer gần64lần logit float, không phải xác suất phần trăm.

Chỉ riêng72 weights8 bit và11 bias32 bit chiếm116 byte theo biểu diễn số thuần. JSON lớn hơn vì có chữ/metadata; FPGA ROM nhúng thành logic theo synthesis, nên116 byte không phải toàn bộ tài nguyên hoặc kích thước bitstream.

## 13. Tính đúng một ví dụ đến đầu ra

Input normal q=[2,68,15,1,1,1]. Neuron ẩn chỉ số1 (đếm từ0) cóweights[-5,15,-49,0,0,6], bias4421:

```text
a1 = -5×2 +15×68 -49×15 +0×1 +0×1 +6×1 +4421 =4702
h1 = clip(floor(4702/128),0,127)=36
```

Tính đủ8 neuron cho hidden=[0,36,16,0,0,28,6,0]. Output Normal dùngweights[-1,16,10,0,0,35,-35,0], bias-57:

```text
score_normal = -1×0 +16×36 +10×16 +35×28 -35×6 -57 =1449
scores = [1449,-985,-498]
argmax=0 -> Normal
```

Ba ví dụ train thực cho kết quả:

| Raw | q | Hidden | Scores [Normal,SYN,Scan] | Chọn |
|---|---|---|---|---|
| [16,136,15,1,1,1] | [2,68,15,1,1,1] | [0,36,16,0,0,28,6,0] | [1449,-985,-498] | Normal |
| [29,48,96,2,1,1] | [3,24,96,2,1,1] | [0,0,0,0,0,16,20,0] | [-197,339,-128] | SYN |
| [13,58,58,2,1,6] | [1,29,58,2,1,6] | [0,15,7,0,0,15,19,0] | [113,-412,299] | Scan |

Đây là phép nhân/cộng theo trọng số đã học, không phải code if(packet_count>...) của model. Argmax chọn score lớn nhất, hòa thì chọn class có chỉ số nhỏ hơn. 1449không phải1449% hoặc xác suất được hiệu chuẩn. Nhận đúng ba dòng train không chứng minh khái quát tốt.

## 14. Điều đáng chú ý trong trọng số hiện tại

Trên toàn miền q0..q5 trong0..127, h0,h3,h4,h7 của bản integer v3 luôn0. W1 của h3/h4/h7 toàn0 và bias âm; h0 chỉ cóhệ số1ởq1 nhưng bias-3584 nên luôn âm. Do đó8 neuron thiết kế nhưng chỉ4 neuron có thể hoạt động. Core chưa được viết lại để bỏ các neuron đó; vẫn chạy kiến trúc8 ẩn/84 chu kỳ.

Cột W1 ứng với f4(dst_count) toàn0, nên bản integer hiện không dùng số IP đích để ra quyết định. Train/validation đều lọc tới một IP bảo vệ cụ thể nên đặc trưng này ít đa dạng. Các điểm này cho thấy không thể đánh giá chất lượng chỉ từ con số8 neuron/83 tham số hoặc mặc định sáu đặc trưng đều được sử dụng hữu ích.

## 15. Một cửa sổ test thực mà v3 nhận sai

File packet_excerpt.csv trong gói minh họa trích11 gói ingress thật từ PCAP v3test01, giây1793448183:8 gói MQTT198.18.0.2->198.18.0.1:1883 và3 gói SYN quét từ198.18.0.3 tới các cổng29/30/31 của cùng đích.

Tổng IPv4 bytes682;11 gói;4 SYN mở(3 SYNquét+1 SYNMQTT);2 nguồn;1 đích;4cổng(gồm 1883). Vì vậy:

```text
raw=[11, floor(682/11), floor(127*4/11), 2,1,4] = [11,62,46,2,1,4]
q=[1,31,46,2,1,4]
scores=[353,-582,222] -> Normal
nhãn kịch bản/PCAP=Scan
```

Đặc trưng và RTL đều tái lập đúng nhưng model chọn sai. Trộn lưu lượng hợp lệ làm giảm tỷ lệ SYN của toàn cửa sổ, số cổng trong mỗi giây cũng nhỏ hơn các mẫu quét đã học. Float cũng chọn Normal. Đây là giới hạn mô hình hiện tại, không được sửa nhãn thành normal để làm đẹp accuracy.

Một đối chứng được dựng riêng: một SYN hợp lệ IPv4 dài40 byte córaw[1,40,127,1,1,1], q[0,20,127,1,1,1], v3scores[-407,240,184] -> SYN flood. Chỉ một gói không đủ chứng minh flood. 1..7 gói SYN cùng đặc điểm có thể cùng q0=0 và cùng vector; cần định nghĩa/đánh giá bằng chứng flood và policy phù hợp, không dùng riêng class_id để chặn.

Sáu thống kê tổng cũng không giữ quan hệ nguồn->đích->cổng, không giữ thứ tự chuỗi gói hoặc ký ức nhiều cửa sổ. Model không trả IP cần chặn. Bộ đếm/quy kết nguồn và CPU policy phải xử lý các việc đó riêng.

## 16. Phần cứng thực hiện model như thế nào?

6×8 +8×3=72phép nhân-cộng mỗi suy luận. Core dùng một đường nhân-cộng dùng chung, làm tuần tự theo FSM. Có8 chu kỳ khởi tạo neuron ẩn,48 MACẩn,3 chu kỳ khởi tạo output,24 MACoutput và1finish:84 chu kỳ sau start được chấp nhận theo testbench.

Tại27 MHz,84 chu kỳ tương đương khoảng 3,11 microsecond cho phần suy luận core nếu clock/implementation đạt yêu cầu. Không phải thời gian từ gói tấn công đầu tiên đến lúc chặn: còn chờ cửa sổ1 giây, xử lý CPU/giao tiếp, điều kiện nhiều cửa sổ và bộ lọc. Chưa đo độ trễ toàn hệ thống trên bo.

Interface: feat48 bit, start, busy, done, class_id2 bit, scores48 bit. Core chốt feat khi nhậnstart, bỏ start mới lúcbusy, done xung một chu kỳ. Scores gồm 3giá trị int16 có dấu, score0 ở16 bit thấp. CPU phải diễn giải signed. Core không tự phân tích Ethernet.

Gowin v3 đã tổng hợp riêng:426 logic(~5%),246 register(~4%),DSP1,BSRAM0,latch0. Report dùng target 50 MHz, estimatedFmax55.9 MHz; SDC trong project ghi27 MHz. Đây chưa phải kết quả sau đặt/đi dây của thiết kế đã ghép hoặc clock đo trên bo. 103I/O trong tổng hợp core riêng bao gồm các tín hiệu dự kiến sẽ nối nội bộ khi ghép, không phải yêu cầu nối103chân ngoại vi trên bo.

## 17. Kết quả nào có thể công bố trung thực?

- Train3083/3083 và validation1829/1829 đúng trên các nguồn đã dùng phát triển; validation đã dùng chọn model nên không gọi là test cuối.
- Somfy IoT-23 dành riêng:705/705 normal, không có SYN/scan trong test này. Baseline cũng đúng 705/705.
- Lab mới v3test01:231 cửa sổ đầy đủ,12rỗng skip,219có dữ liệu; integer/float đúng 214/219=97,72%, normal 114/114, SYN 63/63, scan 37/42. Cả5lỗi là quét chậm thành normal. Baseline219/219.
- Gộp Somfy+lab:919/924=99,46%, nhưng con số đó bị chi phối bởi705 normal; phải báo riêng nguồn/lớp.
- RTL khớp550 vector xuất ban đầu,924 đầu vào test thực và36 probe phản ánh ghép nối; PASS số học không xóa các lỗi ngữ nghĩa.

Chưa chứng minh AI hơn luật ngưỡng, chưa có test nativeIoT-23 SYN độc lập khác capture train, chưa có verticalscan nativeIoT-23 được dùng, chưa đo packetblocking hoặc chốngDoS thực. Các cửa sổ cùng capture tương quan, không coi tất cả dòng là ví dụ độc lập.

## 18. Chạy ví dụ và đọc file nào?

Chạy demo dùng Python3, không cần cài thêm thư viện:

```bash
cd ~/ai_part2
python3 examples/model_v3_walkthrough/demo.py
```

Demo đọc đúng frozenmodel, in raw/q/tổng trước dịch/hidden/scores/class cho ba dòng train thật, một cửa sổ heldout sai thật và một probe SYN đơn lẻ được dựng rõ. Không train hoặc thay model. Gói ZIP minh họa cómodel.json tại cùng thư mục để chạy độc lập.

Các file quan trọng: `gowin/hybrid_v3/model/model.json`(integer), `float_model.json`, `FREEZE.json`, `firmware/ai_quant_v3.h`, `firmware/ai_v3_integration.h`, `src/ai_core_model_v3.v`; code trích xuất ởpart2/features.py, fit ởpart2/hybrid_training.py, suy luận tham chiếu ởpart2/integer.py. Tất cả phải khớp cùng phiên bản khi bàn giao.

Nếu phát triển model mới, cần dữ liệu development đa dạng hơn, định nghĩa SYN flood và policy rõ ràng, kiểm các đối chứng khó, chọn bằng validation và thu test mới sau freeze. Không chỉ tăng số neuron hoặc vá vào một vài dòng đã biết rồi công bố lại accuracy trên chính test đã xem.
