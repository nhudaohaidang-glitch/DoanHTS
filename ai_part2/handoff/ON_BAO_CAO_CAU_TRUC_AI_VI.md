# Ôn báo cáo: cấu trúc AI, đường dữ liệu, lưu trữ và giao thức

Áp dụng cho frozen model v3 e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d. Phân biệt ba mức bằng chứng: mã/core đã kiểm tra; lab Ubuntu đã chạy; kiến trúc hệ thống trong PDF phương án nhưng chưa được xác minh toàn bộ trên bo. Không đổi trọng số hoặc triển khai thêm khối phần cứng trong tài liệu này.

## Bài mở đầu có thể trình bày

Em phụ trách mô hình AI phân loại lưu lượng theo cửa sổ một giây thành bình thường, SYN flood và quét cổng dọc. Dữ liệu lấy từ PCAP IoT-23 có kiểm tra phạm vi nhãn và các phiên lab MQTT trên Ubuntu. Em trích sáu đặc trưng, huấn luyện mạng MLP6–8–3, chuyển trọng số sang số nguyên và triển khai core Verilog. Core nhận sáu byte đặc trưng, tính ba điểm số và trả lớp có điểm cao nhất trong84 chu kỳ theo mô phỏng. Em đã kiểm tra dữ liệu/model, mô phỏng core và tổng hợp riêng bằng Gowin; phần ghép CPU, Ethernet và hiệu quả chặn trên bo chưa được xác minh hoàn chỉnh. V3 đạt214/219 cửa sổ đúng trên test lab mới nhưng còn lỗi SYN đơn lẻ và quét chậm.

## 1. Cấu trúc hệ thống và đường truyền

Theo PDF Phuong_an_tuong_lua_Ethernet_TangNano9K người dùng gửi, phương án tổng thể là bridge Ethernet hai cổng, hai PHY LAN8720/RMII, CPU PicoRV32 và bus Wishbone. Đây là căn cứ kiến trúc đề xuất, không phải bằng chứng tất cả đã ghép/chạy. Ghi chú mới về loader có thể thay đổi phần nạp chương trình; đối chiếu lại với người phụ trách CPU trước buổi báo cáo.

```text
ĐƯỜNG GÓI MẠNG, theo phương án tích hợp:
Nguồn hợp lệ + nguồn thử
 -> cáp Ethernet -> LAN8720 A -> RMII RX/MAC
 -> FIFO đổi miền clock -> buffer/header parser/filter
 -> MAC/RMII TX -> LAN8720 B -> cáp Ethernet -> broker

NHÁNH QUAN SÁT VÀ QUYẾT ĐỊNH:
header -> bộ đếm -> snapshot đặc trưng một giây
 -> thanh ghi đặc trưng -> CPU/Wishbone
 -> chuẩn bị q/ghi thanh ghi AI -> feat48bit/start
 -> core AI -> done/class/scores -> CPU/policy -> thanh ghi bộ lọc
```

CPU không xử lý từng byte/frame thay MAC. AI không làm MQTT broker, không nhận toàn PCAP và không tự chặn IP. Bridge dự kiến không kết thúc phiên TCP/MQTT mà chuyển tiếp/lọc khung giữa hai đầu. ARP phải có chính sách chuyển tiếp để hai máy giao tiếp; không tính ARP vào sáu đặc trưng IPv4 của AI.

| Đoạn | Dữ liệu | Giao tiếp / định dạng | Mức xác nhận |
|---|---|---|---|
| Sensor–broker | Thông điệp nhiệt độ | MQTT trên TCP 1883/IPv4/Ethernet | Đã chạy trong lab mạng ảo Ubuntu |
| Nguồn thử–broker | Yêu cầu SYN/port probes | TCP/IPv4/Ethernet, không cần gửi MQTT payload | Đã chạy trong lab |
| PHY–FPGA MAC | Dữ liệu khung | RMII 2 bit/clock50 MHz, mục tiêu100 Mbps | Theo PDF phương án |
| MAC–parser | Byte và tín hiệu valid/đầu/cuối khung | Dòng dữ liệu8 bit, miền27 MHz sau FIFO | Theo PDF, cần kiểm ghép |
| CPU–ngoại vi AI | Input/control/status/result | Wishbone và thanh ghi ánh xạ bộ nhớ | Theo PDF; chưa đối chiếu wrapper/bản ghép mới nhất |
| Wrapper–core AI | Sáu q, control, ba scores và class | feat48 bit, start/busy/done đồng bộ | Cổng core và handshake đã kiểm mô phỏng |
| FPGA–laptop để log | Bản tin trạng thái | USB-UART 115200,8N1 theo PDF | Giao thức đề xuất; không nhầm với gói Ethernet |

RMII 50 MHz và hệ thống27 MHz là hai miền clock; cần FIFO/đồng bộ đúng. Clock mô phỏng testbench không chứng minh tốc độ chip. Gói chỉ cần đệm theo xử lý frame của đường Ethernet, không giữ toàn bộ lưu lượng một giây để chờ model. Thống kê tích lũy song song; quyết định mới chỉ tác động các gói đến sau khi luật được áp dụng.

## 2. Các câu hỏi về truyền và lưu dữ liệu

### AI nhận dữ liệu gì, không phải toàn bộ gói thì nhận bằng gì?

Core nhận sáu giá trị q trong0..127. Mỗi q chiếm một byte, ghép thành feat48 bit. q0 nằm8 bit thấp, q5 nằm8 bit cao. Sáu giá trị này truyền song song qua tín hiệu nội bộ khi start được chấp nhận, không phải gói TCP hoặc chuỗi ASCII qua UART. Chúng không phải48dây cần đưa ra ngoài board.

### CPU làm sao đưa48 bit vào AI nếu bus32 bit?

Cần wrapper thanh ghi để ghi ít nhất hai từ chứa48 bit, sau đó mới phát start. Đây là nguyên tắc cho bus32 bit; vị trí từng word/offset và cơ chế chốt input phải đối chiếu với wb_ai_regs của bản ghép. Không tự đặt địa chỉ đã triển khai khi chỉ có core standalone.

Theo bản đồ địa chỉ trong PDF: UART ở0x10000000, đặc trưng ở0x20000000, AI ở0x30000000, bộ lọc ở0x50000000. Đây là base đề xuất, chưa xác minh offset hoặc firmware bản mới nhất. Wishbone truyền địa chỉ, dữ liệu, hướng đọc/ghi và tín hiệu yêu cầu/xác nhận. start/busy/done là giao tiếp phía core, không đồng nghĩa toàn giao thức Wishbone.

### Khi nào dữ liệu vào có hiệu lực?

Core nhận start tại cạnh clock khi busy=0, chốt toàn bộ feat. start lúc busy=1 bị bỏ qua. Sau84 chu kỳ theo testbench, done lên một chu kỳ; class và scores giữ tới kết quả mới hoặc reset. Bộ điều khiển cần giữ kết quả/cờ hoàn tất đủ lâu hoặc tạo thanh ghi sticky nếu CPU có thể bỏ lỡ xung done một chu kỳ; việc này thuộc wrapper và cần kiểm tra khi ghép.

### Dữ liệu lưu vào đâu?

| Dữ liệu | Nơi lưu |
|---|---|
| PCAP, log MQTT, CSV huấn luyện, JSON model | Ổ đĩa máy Ubuntu; không nạp toàn bộ lên FPGA |
| Khung Ethernet đang nhận/gửi | Buffer của phần Ethernet, dự kiến BSRAM theo PDF; không nằm trong báo cáo tài nguyên core AI riêng |
| Counter thô và snapshot cửa sổ | Khối đặc trưng/thanh ghi đặc trưng trong hệ thống dự kiến |
| q đang suy luận | Thanh ghi captured48 bit của core |
| Hidden và tổng nhân-cộng |8giá trị hidden 8 bit và accumulator32 bit cùng trạng thái điều khiển |
| Kết quả |3 scores int16 có dấu và class_id2 bit trong thanh ghi |
| Trọng số v3 | Hằng số ROM nhúng trong Verilog bản Gowin; được tổng hợp thành logic theo tool |

Trọng số không tải lại qua mạng cho mỗi mẫu. Bản core v3 hiện không có cơ chế CPU cập nhật trọng số online. Muốn đổi model phải xuất và triển khai lại thiết kế tương ứng. Riêng dữ liệu72 weights int8 +11 bias int32 tương đương116 byte, không tính metadata/trạng thái/buffer. BSRAM0 trong báo cáo AI không có nghĩa toàn hệ thống không cần RAM hoặc framebuffer.

### UART làm gì, có nạp PCAP vào AI qua UART không?

Trong phương án chính, UART phục vụ log; gói mạng đi qua Ethernet. PCAP là dạng ghi trên máy để train/test. PDF có đường dự phòng dùng UART gửi bản ghi header và Linux chặn gói, nhưng không được trình bày đường dự phòng như bridge Ethernet100 Mbps đã hoàn thành. Loader nạp firmware CPU là một chức năng khác với giao tiếp dữ liệu AI; không nhầm UART/loader/Wishbone/RMII thành một đường duy nhất.

## 3. Dataset và bước phân loại

### PCAP gốc có sáu cột chưa?

Chưa. PCAP chứa các gói. Bộ xử lý của nhóm chọn IPv4 hợp lệ đúng hướng tới IP bảo vệ, chia các cửa sổ đầy đủ một giây, đếm và tính ra sáu đặc trưng. Một dòng Zeek flow có thể kéo dài nhiều giây, khác một dòng cửa sổ model. Bảng11đặc trưng chuẩn hóa của người khác không đưa trực tiếp vào core hoặc cắt bừa sáu cột. Tệp dữ liệu có thể có thêm metadata/label; số cột của cả tệp không đồng nghĩa số input model.

### Sáu đặc trưng là gì, tại sao chọn?

| Cột | Công thức | Dấu hiệu hỗ trợ, không phải quy tắc tuyệt đối |
|---|---|---|
| packet_count | N gói IPv4 ingress trong giây | Mức lưu lượng |
| mean_ip_bytes | floor(sum IPv4 TotalLength/N) | Gói điều khiển nhỏ so với dữ liệu ứng dụng |
| syn_ratio_q127 | floor(127*SYN_open/N) | Mức xuất hiện yêu cầu mở TCP |
| src_count | Số IP nguồn khác nhau | Phân bố nguồn ở mức số đếm |
| dst_count | Số IP đích khác nhau | Phạm vi đích; hiện lọc một IP nên có ít thông tin |
| dst_port_count | Số port TCP/UDP đích khác nhau | Dấu hiệu thử nhiều dịch vụ |

SYN_open là SYN=1 ACK=0, mẫu số là tất cả IPv4 hợp lệ, không chỉ gói tấn công/TCP. Không tính ARP/chiều trả về trong các cột đó; loại fragment/truncated IP và ghi thống kê. Phần mềm tham chiếu dùng distinct exact; cần đối chiếu nếu phần cứng dùng bảng/bitmap có giới hạn hoặc va chạm. Các đặc trưng được chọn theo ý nghĩa mạng và chi phí FPGA, chưa chứng minh đây là lựa chọn tối ưu.

### Chia/chuẩn hóa ra sao?

q=clip(raw//[8,2,1,1,1,1],0,127), đúng một lần. Ví dụ[13,58,58,2,1,6] thành[1,29,58,2,1,6]. Fit float dùng q/128; core integer nhận q trực tiếp vì scale đã nằm trong weights/bias/shift. Bỏ RAW packet_count=0; không bỏ tất cả q0=0 vì 1..7 gói vẫn hợp lệ. Header C nhận tổng byte và số SYN, không nhận mean/ratio thay thế các số đếm đó.

### Nhãn đến từ đâu, vì sao đã có nhãn còn cần AI?

Lab có kịch bản nguồn chạy normal/SYN/scan và thời gian biết trước; source.log và PCAP xác nhận hoạt động thực. IoT-23 dùng nguồn benign và đoạn DDoS đã kiểm flags/timing phù hợp SYN. Không đổi mọi DDoS thành SYN hoặc quét ngang thành quét dọc.0=Normal,1=SYN flood,2=vertical scan là quy ước của dự án này; class của dataset bạn gửi phải kiểm mapping riêng.

Nhãn y là đáp án cho các ví dụ cũ để học và để đánh giá. Lúc suy luận model chỉ nhận X, không đọc y. Đầu vào mới không có đáp án sẵn; đó là lúc model dự đoán. Nhãn cửa sổ không nói mọi gói trong cửa sổ đều độc hại, cũng không tự chứng minh dịch vụ đã bị DoS.

### Huấn luyện gì, lưu cái gì sau khi học?

MLP6 input–8 hidden ReLU–3 output,83 tham số gồm 48W1+8b1+24W2+3b2. scikit-learn/L-BFGS điều chỉnh weights/bias bằng loss trên train; chọn bằng validation. V3 chọn seed 11,alpha 0.01 trong9ứng viên; alpha là phạt L2. Chuyển weights int8, bias/accumulator int32, hidden 0..127 và scores int16, shift1=7,shift2=0. Sau đó chốt model và test mới. FPGA chỉ suy luận, không học lại khi chạy.

Model tạo ba scores, chọn lớn nhất, hòa chọn chỉ số lớp nhỏ hơn. Scores không phải xác suất phần trăm; số âm không có nghĩa lỗi. Khi CPU đọc scores phải dùng int16 có dấu. Một ví dụ train thật raw[13,58,58,2,1,6] cho scores[113,-412,299] và chọn Scan.

### V3 học từ dữ liệu nào, có phải toàn IoT-23 không?

Train3083 cửa sổ:182lab +2880Hue benign +21native SYN. Validation1829 cửa sổ:210lab cũ +1619Echo benign. Train theo lớp2958Normal/73 SYN/52Scan; do đó Scan có trong lab, không có nhờ đổi nhãn IoT-23. Chia theo nguyên capture; dữ liệu challenge/holdout cũ đã xem được khai báo lại là development v3.

Sau lượng tử train có 55/27/25 điểm khác nhau theo lớp, lặp để fit165 dòng cân bằng. Lặp không tạo tình huống mới. Native SYN là một đợt22 giây và21 cửa sổ của nó cùng q do bão hòa, không phải21 đợt độc lập. ZIP đọc nhỏ2.901 dòng chỉ gồm Hue+đoạn SYN, không phải toàn bộ dataset đã huấn luyện ba lớp.

### Model biết nguồn nào cần chặn không?

Không. Số IP nguồn bằng2 chỉ là số đếm, không chứa hai địa chỉ IP. Model trả lớp cho toàn cửa sổ; source attribution phải nằm ở phần khác. PDF đề xuất SUSPECT_IP và CONFIRM_CNT cho firmware xác nhận; chưa khẳng định bản ghép đã chạy. AI không tự ghi blacklist. Quyết định chặn cần nguồn cụ thể, mức bằng chứng và thời gian hết hạn luật.

## 4. Hai kiểu tấn công và mô hình thử

### DoS và port scan dùng giao thức gì?

DoS là mục tiêu gây từ chối dịch vụ, không phải tên giao thức. Bài này chọn kỹ thuật TCP SYN flood. Port scan là thăm dò cổng, có nhiều cách; bài này chọn TCP SYN vertical scan. **Cả hai kịch bản hiện dùng TCP trên IPv4/Ethernet.** Không phải UDP flood hoặc UDP scan. MQTT là dịch vụ bị bảo vệ, lưu lượng tấn công không cần gửi bản tin MQTT hợp lệ.

### Tấn công vào đâu?

Lab Ubuntu đã chạy: sensor198.18.0.2 gửi MQTT hợp lệ tới broker198.18.0.1:1883; source198.18.0.3 gửi SYN vào cổng1883 hoặc quét nhiều cổng trên cùng broker. Các môi trường mạng ảo nối Linux bridge, capture phía broker; không có FPGA inline trong phép thu đó. Phương án vật lý đặt FPGA bridge giữa phía nguồn và broker. Broker là đích thử nghiệm, không phải core AI. Bridge không tự làm broker hoặc kết thúc phiên MQTT.

### SYN flood khác scan thế nào nếu đều gửi SYN?

Flood thường tập trung lượng yêu cầu lớn vào một dịch vụ; scan thử nhiều cổng để tìm dịch vụ. Dùng tỷ lệ SYN cùng số gói và số cổng, không chỉ nhìn một cờ SYN. Scan có thể không làm dịch vụ ngừng hoạt động và không tự chứng minh đã khai thác được lỗ hổng. Một SYN đơn lẻ cũng có tỷ lệ100% nhưng chưa đủ bằng chứng flood.

### Có phải đã thử DDoS và chống DoS thành công?

Nguồn lab hiện là một nguồn phát tấn công mô phỏng, không phải chứng minh DDoS nhiều máy. Có nhãn từ kịch bản SYN không đồng nghĩa broker đã mất dịch vụ. Cần đo MQTT thành công/thất bại, độ trễ và tài nguyên, rồi so có/không biện pháp bảo vệ. Hiện chưa đo đầy đủ hiệu quả blocking/end-to-end trên bo. Không nói97,72%classification là97,72%gói được chặn.

## 5. Thời gian, tài nguyên và giới hạn

84 chu kỳ là riêng core từ start được chấp nhận tới done, gồm 72 MAC và điều khiển. Ở27 MHz nếu triển khai đạt yêu cầu thì khoảng 3,11 microsecond. Còn chờ chốt cửa sổ một giây, snapshot, CPU/bus, xác nhận và cập nhật lọc. Độ trễ phát hiện/chặn toàn hệ thống chưa đo. Tốc độ Ethernet100 Mbps không suy ra từ thời gian inference; đường frame và đường quyết định có nhiệm vụ khác nhau.

Core v3 synthesis riêng:426 logic(~5%),246 register(~4%),DSP1,BSRAM0,latch0. Report có target 50 MHz và estimatedFmax55.9 MHz; SDC được cung cấp27 MHz. Đây không phải routed timing hoặc clock đo trên bo. Core dùng một đường MAC tuần tự, không phải8 neuron tương ứng8DSP vật lý.

8 neuron ẩn là lựa chọn kiến trúc, chưa chứng minh tối ưu; bản integer hiện có 4 neuron luôn0 và cột weights dst_count toàn0. Không tuyên bố cả sáu đặc trưng đều có đóng góp hoặc tám neuron đều hoạt động hữu ích.

Test lab mới:214/219đúng, Normal114/114,SYN 63/63,Scan37/42; baseline219/219. Test Somfy705/705 normal, không chứa hai lớp tấn công. V3 còn nhận SYN hợp lệ đơn lẻ thành flood, bỏ sót5 cửa sổ scan chậm trộn MQTT. Float cũng sai ở các trường hợp đã kiểm đó; RTL khớp score model không chữa lỗi ngữ nghĩa. Chưa chứng minh AI hơn baseline hoặc khái quát mọi mạng.

## 6. Những thứ cần xác nhận với người phụ trách ghép trước báo cáo

1. Phương án Wishbone và các base địa chỉ trong PDF còn đúng với bản CPU hiện tại không? Wrapper input/control/status AI và cơ chế giữ done có gì đã chạy thật?
2. Clock thực tế của AI/CPU, cách đồng bộ RMII–hệ thống, snapshot các bộ đếm có nhất quán không?
3. Sáu đặc trưng phần cứng có đúng chiều, đơn vị, mốc cửa sổ, SYN count, distinct và divisor như Python không? Phần nào đã mô phỏng/đo?
4. Theo dõi IP nghi vấn và luật chặn đã kiểm chứng tới đâu? Những phép thử nào trên bo thực sự đã chạy?

Nếu chưa có xác nhận, trình bày đúng: “Theo tài liệu phương án nhóm dùng ..., riêng phần em đã kiểm tra là core AI với giao tiếp ..., phần ghép này đang cần kiểm chứng.” Không chọn tên bus hoặc bịa offset/độ trễ để trả lời cho đủ.
