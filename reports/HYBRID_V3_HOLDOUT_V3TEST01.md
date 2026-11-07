# Chẩn đoán AI v3 trên test mới v3test01

Ngày kiểm tra: 31/10/2026. Nguồn: gói ai_v3_diagnostic.zip người dùng gửi sau khi chạy đủ 11 phiên lab mới. Chỉ đọc dữ liệu; không chạy mã từ gói tải lên, không huấn luyện lại, không đổi nhãn, trọng số hoặc luật ngưỡng.

Model SHA256: `e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d`.

## Kết quả đã tái lập

| Nguồn | Bình thường đúng | SYN đúng | Scan đúng | Accuracy integer |
|---|---:|---:|---:|---:|
| Lab mới, 11 phiên | 114/114 | 63/63 | 37/42 | 214/219 = 97,72% |
| IoT-23 Somfy dành riêng | 705/705 | Không có | Không có | 100% trên lớp bình thường |
| Gộp hai nguồn | 819/819 | 63/63 | 37/42 | 919/924 = 99,46% |

Lab macro-F1 = 0,971750; FPR = 0/114. Chỉ số trung bình recall theo capture rồi theo lớp = 96,03%, khác accuracy. Toàn bộ 5 lỗi là scan thành normal. Scan chậm đúng 16/21 = 76,19%; scan nhanh đúng 21/21. Recall scan chung = 37/42 = 88,10%. Luật ngưỡng đã chốt từ validation đạt 219/219 trên lab này; chưa có bằng chứng AI tốt hơn luật ngưỡng.

## Kiểm tra dữ liệu và phép tính

- Cả 11 tệp trong thư mục model tải lên giống từng byte với bản v3 đã chốt trong repository.
- Đọc lại cả 11 PCAP bằng mã trích xuất đã kiểm tra: CSV 231 cửa sổ và metadata tái lập giống từng byte/nội dung với bản người dùng gửi. Loại đúng 12 cửa sổ không gói, còn 219; không tính các cửa sổ rỗng thành dự đoán normal đúng.
- Đánh giá lại bằng model và cache Somfy đã chốt tái lập chính xác toàn bộ metrics và 924 dòng dự đoán tải lên. Float và integer không khác dự đoán ở bất kỳ dòng nào.
- Tất cả capture.log ghi 0 packets dropped by kernel. Một số PCAP có đảo timestamp rất nhỏ, tối đa khoảng 90 microsecond; bộ trích xuất giữ mỗi gói trong cửa sổ timestamp của chính nó. Không có fragment/truncated packet bị loại trong phiên scan chậm.
- Decoder Ethernet/IPv4/TCP riêng dùng RawPcapReader và struct, không dùng helper tính đặc trưng, tái xác nhận toàn bộ 21 cửa sổ scan chậm.
- Core Verilog ROM v3 đã chốt, chạy bằng Icarus với 924 vector từ đầu vào thực tế của lần test này: `PASS vectors=924 cycles_min=84 cycles_max=84`. Đây là kiểm tra số học/handshake trong mô phỏng, chưa phải synthesis, routed timing hoặc thử trên bo.

## Nguyên nhân 5 lỗi

Trong mỗi cửa sổ lỗi có 3 gói TCP SYN từ `198.18.0.3` đến 3 cổng khác nhau của cùng đích `198.18.0.1`, trộn với 8 gói MQTT hợp lệ từ `198.18.0.2` đến cổng 1883. Đây vẫn là vertical scan; PCAP chứng minh hoạt động quét thực sự xảy ra, không phải cửa sổ tấn công rỗng.

| Đặc trưng | Giá trị |
|---|---:|
| Số gói IPv4 ingress | 11 |
| Trung bình IPv4 TotalLength, lấy phần nguyên | 62 byte |
| floor(127 × SYN mở / tất cả gói ingress) | floor(127 × 4 / 11) = 46 |
| Số IP nguồn / IP đích | 2 / 1 |
| Số cổng đích TCP/UDP | 4, gồm 3 cổng quét và MQTT 1883 |

Bốn SYN gồm 3 SYN quét và 1 SYN mở kết nối MQTT. Không được diễn giải 4 cổng đích là 4 cổng tấn công, hoặc tỷ lệ SYN là tỷ lệ chỉ trong luồng tấn công.

Sau divisors `[8,2,1,1,1,1]`, cả 5 cửa sổ thành cùng vector `[1,31,46,2,1,4]`. Vector này không xuất hiện nguyên vẹn trong tập train hoặc validation. Scores integer `[Normal,SYN,Scan] = [353,-582,222]`: model chọn Normal; scores không phải xác suất. Float cũng chọn Normal. Điều này chỉ ra lỗi phân loại của ứng viên v3 tại tổ hợp đặc trưng mới, không phải mất chính xác do chuyển sang integer hoặc sai khác giữa Python và RTL.

16 cửa sổ scan chậm còn lại có vector `[1,30,52,2,1,5]`, scores `[241,-517,272]` và được chọn Scan. Lưu lượng quét thưa hơn cùng việc trộn MQTT làm tỷ lệ SYN và số cổng mỗi giây giảm, đưa các mẫu lỗi sang phía Normal trong ranh giới quyết định đã học. Các mẫu scan chậm dùng phát triển trước đây chủ yếu có 6–7 cổng đích mỗi giây; tập đó chưa bao phủ tốt tổ hợp mới. Đây là giới hạn quan sát được của model, chưa phải chứng minh đầy đủ nguyên nhân thống kê hoặc hiệu quả của một cách sửa.

| Epoch giây lỗi | Cổng quét trong giây đó; cùng đích 198.18.0.1 |
|---|---|
| 1793448183 | 29, 30, 31 |
| 1793448187 | 44, 45, 46 |
| 1793448192 | 63, 64, 65 |
| 1793448196 | 78, 79, 80 |
| 1793448200 | 93, 94, 95 |

Source.log ghi 93 gói quét/24,657 giây, khoảng 3,77 gói/giây, requested_pps=4. Bộ phát quy định PPS là trần và không bù burst sau khi VM chậm; mỗi cửa sổ có 3 hoặc 4 gói quét phù hợp PCAP. Không sửa nhãn hoặc loại 5 cửa sổ để làm tăng accuracy.

Luật ngưỡng có port_threshold=3 và syn_ratio_q127_threshold=32 từ trước test, nên nhận các vector lỗi là Scan. Kết quả đó giải thích vì sao baseline thắng trong phép thử này, chưa chứng minh không báo nhầm ở các mạng khác.

## Việc tiếp theo

Giữ v3 và kết quả này làm mốc kiểm chứng. Có thể tiếp tục synthesis riêng project `ai_part2/gowin/hybrid_v3/ai_core_v3.gprj` và chuẩn bị ghép, nhưng phải ghi rõ điểm yếu quét chậm; không coi v3 là bộ phát hiện đã hoàn thiện hoặc bộ chặn gói đã thử trên bo. Không dùng lại số tài nguyên/Fmax v2 cho v3.

Nếu phát triển ứng viên sau, thu thêm phiên development có tốc độ quét thấp, nhiều mức MQTT nền và đối chứng bình thường nhiều cổng hợp lệ. Chọn model chỉ bằng train/validation, chốt trước khi thu test mới. Nếu dùng v3test01 hoặc kết quả Somfy đã xem để chỉnh model, các nguồn đó trở thành development cho ứng viên sau, không tiếp tục gọi là test độc lập của ứng viên đó. Không thêm luật OR/chỉnh ngưỡng chỉ để chữa 5 dòng rồi công bố 100% trên cùng test.

Mọi thao tác trên đây chỉ là đánh giá ngoại tuyến. Phiên scan chậm vẫn có 25/25 thao tác MQTT ghi thành công; không có bằng chứng đo mức suy giảm dịch vụ, hành động chặn Ethernet hay độ trễ phát hiện/chặn trên FPGA.
