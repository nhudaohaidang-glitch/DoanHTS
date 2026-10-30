# V3 — IoT‑23 kết hợp lưu lượng lab, giữ đúng SYN flood và vertical scan

Model SHA256: e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d.

Đã huấn luyện/chốt ứng viên mới. Chưa hoàn thành test lab mới đủ ba lớp hoặc đo phần cứng. Không gọi đây là mô hình ba lớp huấn luyện hoàn toàn bằng IoT‑23.

| Bộ | IoT‑23 | Lab có kiểm soát | Mục đích |
|---|---:|---:|---|
| Train | Hue4 normal2880 + Syn34 có bằng chứng21 | challenge01 cũ182 | Học trọng số |
| Validation | Amazon Echo5 normal1619 | v2test01 cũ210 | Chọn model số nguyên |
| Test ngoại miền dành riêng | Somfy01 normal705 | Chưa có | Kiểm normal trên capture mới sau freeze |
| Test lab mới | Không áp dụng | 11 phiên chưa thu | Kiểm đủ ba lớp sau freeze |

Challenge v1 và holdout v2 cũ đã được chuyển thành dữ liệu PHÁT TRIỂN v3; không dùng lại để công bố test độc lập v3. Không dùng quét ngang IoT‑23 để giả thành quét dọc.

SYN IoT‑23 là đoạn gốc capture34:40568gói SYN=1 ACK=0 tới71.61.66.148:80, khớp luồng Malicious/DDoS, kéo dài22giây; giữ21cửa sổ hoàn chỉnh. Chỉ một đợt tấn công, tất cả q giống nhau do bão hòa số gói; chưa có SYN IoT‑23 từ capture khác để test. Vertical scan đến từ các phiên lab thực đã thu, không phải nhãn scan ngang đổi tên.

Sáu đặc trưng vẫn packet-derived ingress IPv4, cửa sổ1giây, exact distinct; input divisors[8,2,1,1,1,1]. Khối trích xuất phần cứng chưa cần đổi ngữ nghĩa vì v3 giữ hợp đồng này. Chỉ các cửa sổ RAW packet_count>0 đủ điều kiện suy luận; báo rõ số giây rỗng bị skip, không tính chúng là normal đúng để làm đẹp accuracy.

Train gốc3083cửa sổ thuộc9capture; validation1829cửa sổ thuộc11capture. Huấn luyện cân bằng các điểm lượng tử phân biệt theo lớp:55normal,27SYN,25scan; lặp thành165điểm fit để cân bằng loss. Lặp không tạo dữ liệu hay phiên độc lập mới. Metrics được tính trên toàn bộ cửa sổ gốc, không chỉ các điểm fit.

9ứng viên: seeds11,23,47 và alpha0.01,0.1,0.001. Chọn bằng recall cân bằng capture/lớp trên validation, hòa thì macro-F1 rồi FPR nguồn xấu nhất, thứ tự đã khai báo trong protocol. Chốt seed11/alpha0.01. Grid có1convergence warning; kiểm tái lập riêng ứng viên đã chọn hội tụ ở189iterations, không warning, toàn bộ tham số số nguyên khớp bản đã freeze. Không đổi weights sau khi xem test Somfy.

Kết quả float/integer validation:1829/1829, FPR0. Đây là VALIDATION, không phải test cuối. Somfy01 chưa dùng chọn mô hình:705/705normal, FPR0; baseline cũngFPR0. Trên CHÍNH705cửa sổ đó, v2 nhầm219thànhscan (FPR31.06%). Đây là cải thiện trên một capture benign, không chứng minh v3 hơn baseline hoặc đạt95%mọi mạng/loại tấn công.

Core6–8–3,550vector PASS cả bản HEX và ROM nhúng,84chu kỳ. Divisors không đổi nhưng shift1=7, shift2=0, hidden_scale=8, score_scale=64. Firmware dùng ai_v3_prepare_window/ai_quant_v3.h của cùng project. Scores int16 có dấu, không phải xác suất. Giữ guard RAW packet_count==0; 1..7gói vẫn hợp lệ dù q0=0. Không tạo luật chặn mới từ cửa sổ rỗng, TTL/giao dịch đang chạy xử lý độc lập.

Project mới: gowin/hybrid_v3/ai_core_v3.gprj. Chỉ dùng một ai_core khi tích hợp, không thêm cả corev2vàv3. Báo cáo resource/Fmaxv2 không đại diện v3; cần synthesis/routed timing mới. Chưa có FPGA/CPU/bus/bridge blocking hoặc end-to-end latency của v3. Profile lab test mới còn cần chạy trên Ubuntu của người dùng vì cloud không tạo được namespace mạng thật.
