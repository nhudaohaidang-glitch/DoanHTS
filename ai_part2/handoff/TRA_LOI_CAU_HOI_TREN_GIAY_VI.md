# Trả lời các ý trong giấy và tóm tắt AI v3

Tài liệu trả lời theo model v3 đang chốt, không sửa mô hình hoặc thay đổi phần cứng. Chữ ở mục datasheet/dataset và ghi chú LCD có chỗ chưa rõ; dưới đây giải thích cả bộ dữ liệu, bảng thông số core và giới hạn phần thiết kế chưa được xác nhận.

## 1. Làm rõ dataset và datasheet

Dataset là bộ dữ liệu dùng học/đánh giá. Datasheet là bảng thông số kỹ thuật. Hai từ khác nhau.

V3 dùng PCAP IoT-23 kết hợp các phiên lab Ubuntu có kiểm soát, giữ ba lớp0=Normal,1=SYN flood,2=TCP vertical scan. Dữ liệu đầu vào mạng là sáu thống kê của cửa sổ một giây, không phải một dòng Zeek flow. Vertical scan lấy từ lab, không đổi nhãn quét ngang IoT-23 thành quét dọc. Đoạn IoT-23 dùng cho SYN đã kiểm flags và luồng gốc DDoS, không quy mọi DDoS thành SYN.

| Phần | Nguồn | Số cửa sổ |
|---|---|---:|
| Train | Lab challenge01 cũ | 182 |
| Train | IoT-23 Philips Hue benign | 2880 |
| Train | Đoạn native SYN capture34 | 21 |
| Train tổng | 9 capture | 3083 |
| Validation | Lab v2test01 cũ + IoT-23 Amazon Echo benign | 1829 |
| Test benign dành riêng | IoT-23 Somfy | 705 |
| Test lab mới v3test01 | 11 phiên mới, đủ ba lớp | 219 không rỗng |

V1 challenge và V2 holdout cũ trở thành development cho V3. Chia theo nguyên capture, không trộn ngẫu nhiên các giây liền nhau giữa các tập. Sau lượng tử hóa, train có 55/27/25 điểm khác nhau theo ba lớp, lặp thành165 điểm fit để cân bằng; không phải dữ liệu mới. Đoạn SYN IoT-23 chỉ từ một đợt tấn công, nên số dòng không đại diện số tình huống độc lập.

Ảnh dataset 66 MB mới có 11đặc trưng chuẩn hóa và cột class chưa xác minh mapping; chưa nhận toàn bộ tệp/mã xử lý và chưa dùng nó để huấn luyện v3. Không áp quy ước0/1/2 của v3 cho ảnh đó khi chưa có bằng chứng.

## 2. Trích chọn đặc trưng là làm gì?

Trích xuất: đọc gói và tính các con số. Chọn đặc trưng: quyết định những con số nào đưa vào mạng. Hiện sáu đặc trưng được chọn theo ý nghĩa mạng và khả năng triển khai FPGA; chưa có chứng minh đây là bộ tối ưu bằng một nghiên cứu chọn đặc trưng tự động.

Chỉ tính IPv4 hợp lệ chiều tới IP bảo vệ, cửa sổ đầy đủ một giây; bỏ fragment/truncated IP và ghi thống kê. Không tính ARP hoặc chiều trả về vào sáu thống kê này. Distinct dùng đếm chính xác trong tham chiếu phần mềm.

| Đặc trưng | Công thức / ý nghĩa | Lý do quan sát |
|---|---|---|
| packet_count | N gói hợp lệ trong một giây | Mức lưu lượng |
| mean_ip_bytes | floor(tổng IPv4 TotalLength/N) | Phân bố kích thước gói |
| syn_ratio_q127 | floor(127*S/N), SYN=1 ACK=0 | Tỷ lệ yêu cầu mở TCP |
| src_count | Số IP nguồn phân biệt | Số nguồn xuất hiện |
| dst_count | Số IP đích phân biệt | Phạm vi đích |
| dst_port_count | Số cổng đích TCP/UDP phân biệt | Dấu hiệu thử nhiều dịch vụ |

Ví dụ thực: một giây có 8 gói MQTT +3 gói SYN quét; tổng 11 gói/682IPv4 byte;4 SYN mở gồm 1 SYNMQTT;2 nguồn/1 đích/4cổng. Raw=[11,62,46,2,1,4]. Một mẫu có thể chứa cả lưu lượng hợp lệ và tấn công. Nhãn đến từ kịch bản/PCAP, không mặc định mọi gói trong một cửa sổ tấn công đều độc hại.

Preprocessing v3: q=clip(raw//[8,2,1,1,1,1],0,127). Pack q0 vào8 bit thấp, q5 vào8 bit cao của feat48 bit, đúng một lần. Mẫu RAW N=0 skip; không bỏ mọi q0=0 vì1..7 gói vẫn hợp lệ.

## 3. Giao thức và kiểu tấn công

Ethernet là lớp truyền frame; IPv4 xác định nguồn/đích; TCP thiết lập/vận chuyển kết nối; MQTT là giao thức ứng dụng cần bảo vệ. SYN flood và vertical scan là kỹ thuật tấn công/thăm dò dùng TCP trong kịch bản này, không phải tên giao thức ứng dụng riêng.

| Kịch bản | Hoạt động | Đích trong lab | Ý định |
|---|---|---|---|
| Normal | Kết nối và gửi nhiệt độ MQTT, có SYN/ACK hợp lệ | 198.18.0.1:1883 | Dịch vụ bình thường |
| SYN flood scenario | Gửi nhiều SYN mở, không hoàn tất bắt tay như client hợp lệ | TCP198.18.0.1:1883 | Tạo áp lực thiết lập kết nối |
| Vertical scan | SYN tới nhiều cổng của cùng một IP | 198.18.0.1, nhiều cổng | Tìm dịch vụ/cổng mở |

Quét cổng là hoạt động thăm dò, không tự chứng minh đã khai thác lỗ hổng. Một SYN hợp lệ không chứng minh flood. Nguồn lab hiện chỉ một máy nguồn tấn công mô phỏng, không tuyên bố đã dựng tấn công phân tán DDoS thực sự. Nhãn SYN trong lab biểu thị kịch bản phát lưu lượng SYN; phải đo thêm tác động dịch vụ mới kết luận DoS thành công.

PCAP IoT-23 có đoạn SYN tới71.61.66.148:80 dùng train; đó là đọc lại dữ liệu công bố có sẵn, khác đích1883 trong lab hiện tại.

## 4. Mô hình tấn công: ai tấn công ai, qua đâu?

Lab đã chạy hoàn toàn trong Ubuntu:

```text
Cảm biến mô phỏng 198.18.0.2 ----\
                                  Linux bridge -> MQTT broker 198.18.0.1:1883
Nguồn thử nghiệm 198.18.0.3 -----/                   |
                                                     -> PCAP -> sáu đặc trưng -> AI offline
```

Đây là ba môi trường mạng riêng trên cùng Ubuntu, không bắt buộc ba máy thật. Chúng có mạng lab riêng, không nối uplink/default route Internet. Capture được thu phía broker. Luồng chính được bảo vệ là từ cảm biến tới broker; nguồn thử tạo lưu lượng cùng hướng tới broker. Đích bị thử nghiệm là dịch vụ phía broker, không phải neuron AI.

Phương án tích hợp phần cứng cần kiểm chứng tiếp:

```text
Cảm biến + nguồn thử -> Ethernet vào -> FPGA bridge/filter -> Ethernet ra -> broker
                                            |
                                            -> parser/bộ đếm -> đặc trưng1giây
                                                                  |
                                                                  -> AI -> CPU/policy
                                                                               |
                                                                               -> luật lọc
```

AI trả lớp/điểm cho cửa sổ, không trả IP tấn công từ sáu con số đếm. CPU phải có thông tin quy kết nguồn riêng, điều kiện đủ bằng chứng và chính sách hết hạn luật. Chưa có xác minh toàn bộ luồng CPU/bus/bridge/chặn gói trên bo; không mô tả sơ đồ dự kiến như thử nghiệm đã hoàn thành.

## 5. Thời gian xử lý là bao nhiêu?

| Khâu | Thông tin hiện có |
|---|---|
| Gom đặc trưng | Cửa sổ1 giây; chờ chốt thống kê của cửa sổ |
| Suy luận core | 84 chu kỳ sau start được chấp nhận theo mô phỏng |
| Quy đổi nếu clock27 MHz | Khoảng3,11 microsecond cho riêng core, nếu implementation đạt yêu cầu |
| CPU, cập nhật bộ lọc, chuyển tiếp | Chưa đo trên hệ thống đã ghép |
| Từ gói đầu tiên tới chặn | Chưa đo; không lấy 3,11 microsecond làm độ trễ toàn hệ thống |

Còn ảnh hưởng mốc cửa sổ, thời điểm gói tới, điều kiện xác nhận nhiều cửa sổ và giao tiếp. Testbench có clock10ns chỉ để kiểm logic, không chứng minh chạy100 MHz trên chip.

## 6. Bảng thông số core AI v3

| Mục | Giá trị |
|---|---|
| Loại model | MLP truyền thẳng, một tầng ẩn ReLU |
| Kiến trúc | 6 input–8 hidden–3 output |
| Tham số học | 48+8+24+3=83 |
| Huấn luyện | scikit-learn, L-BFGS, seed 11, alpha 0.01, chọn bằng validation |
| Input | Sáu q trong0..127, feat48 bit |
| Output | class_id2 bit,3scores int16 có dấu |
| Weights / bias / accumulator | int8 / int32 / int32 |
| Shift1 / Shift2 | 7 / 0 |
| Các cổng điều khiển | clk,rst_n,start,busy,done |
| RTL | Một đường nhân-cộng dùng chung,72 MAC/84 chu kỳ |
| Thiết bị mục tiêu | Tang Nano9K, GW1NR-LV9QN88PC6/I5 |
| Synthesis riêng v3 | 426 logic(~5%),246 register(~4%),DSP1,BSRAM0,latch0 |
| Timing báo cáo synthesis | Target50 MHz, estimatedFmax55.9 MHz; SDC được cung cấp27 MHz |

Scores không phải xác suất, core không tự ghi luật chặn. Có8 neuron ẩn theo kiến trúc nhưng4 neuron của bản integer hiện luôn0 trong miền input hợp lệ; dst_count có các hệ số bằng0. Không coi83 vị trí tham số là83giá trị đều có ích hoặc chứng minh lựa chọn8 neuron tối ưu.

## 7. Kết quả và giới hạn phải nói rõ

Test Somfy:705/705 normal, chỉ có lớp bình thường. Test lab mới:normal 114/114,SYN 63/63,scan 37/42,tổng 214/219=97,72%; baseline219/219. Các5lỗi là scan chậm trộn MQTT thành normal. Một probe SYN hợp lệ đơn lẻ cũng bị v3 gán SYN flood ở cả float/integer. V2 có thêm nhiều lỗi cảm biến/ACK/scan đã tái lập.

Core tính khớp model trên 550 vector ban đầu,924 đầu vào test và36 probe phản ánh ghép nối; đây là đúng số học, không xóa lỗi phân loại. Chưa chứng minh AI hơn baseline, chưa có test SYN IoT-23 độc lập khác đợt train, chưa đo chống gián đoạn dịch vụ hoặc blocking trên bo. Model và các kết quả đã chốt được giữ nguyên.

## 8. Ghi chú UART, bus loader và hiển thị

UART là giao tiếp nối tiếp; loader là chức năng nạp chương trình/dữ liệu. Cần biết khối nào đang được nói tới trước khi kết luận có thể bỏ UART. Nếu mục tiêu là CPU trao đổi với AI qua bus nội bộ, cần wrapper/thanh ghi theo bus nhóm chọn: ghi input, phát start, đọc busy/done/class/scores. Core hiện chỉ có các cổng trực tiếp kể trên; chưa chốt địa chỉ MMIO hoặc giao thức bus trong phần AI này. Không sửa UART/loader chỉ từ ghi chú ảnh.

Dòng LCD/còi/OLED có gạch sửa nên chưa xác định chắc phương án hiển thị đã chốt. Các khối đó là đầu ra hiển thị/cảnh báo; có thể do CPU điều khiển, không đổi kiến trúc/trọng số AI. Mã case/Q ở đầu trang có dạng bộ đếm, không phải phép học hoặc tính trọng số; muốn giải thích code chính xác cần bản code đầy đủ.

## 9. Đoạn trình bày ngắn

Phần AI sử dụng mạng MLP6–8–3 có 83 tham số, phân loại cửa sổ một giây thành bình thường, SYN flood và quét cổng dọc. Sáu đặc trưng gồm số gói, độ dài IPv4 trung bình, tỷ lệ SYN mở, số IP nguồn, số IP đích và số cổng đích khác nhau. Dữ liệu học kết hợp PCAP IoT-23 có kiểm tra phạm vi nhãn với lưu lượng thu trong lab Ubuntu; quét dọc lấy từ lab. Model được huấn luyện offline rồi chuyển sang số nguyên và triển khai bằng Verilog trên Tang Nano9K. Core mất84 chu kỳ tính;97,72% là kết quả phân loại trên 219 cửa sổ lab mới, không phải tỷ lệ chặn gói. V3 còn báo nhầm SYN đơn lẻ và bỏ sót một số quét chậm. AI chỉ trả kết quả phân loại; CPU/policy và bộ lọc Ethernet xử lý nguồn và hành động chặn, phần tích hợp đó cần được kiểm chứng tiếp.
