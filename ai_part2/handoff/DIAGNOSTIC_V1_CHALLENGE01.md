# Chẩn đoán AI v1 trên challenge01 — 29/10/2026

Nguồn: ai_v1_diagnostic.zip do người 2 gửi. Không chạy mã Python trong tệp tải lên; dùng bộ đọc PCAP và mô hình số nguyên của repository. Không đưa PCAP riêng của người dùng vào Git.

## Đã kiểm chứng

- Model SHA256: `b67f6de6b847a4d2500e2af130c9e31091c92a9cbd3f68de84fe0a31d2a59007`. Khớp bản Gowin v1 đã review.
- Tính lại đúng toàn bộ 182 dự đoán, scores và đầu vào lượng tử so với predictions.jsonl đã gửi.
- Đọc lại độc lập 2 PCAP được gửi: normal_retry và scan_slow. SHA256 khớp metadata; toàn bộ 52 hàng đặc trưng của hai phiên khớp CSV. Năm PCAP còn lại không có trong gói; chỉ có CSV/log để phân tích.
- Cả 7 capture.log ghi 0 packets dropped by kernel. Điều này không chứng minh không có mất gói ở mọi khâu khác.
- Không có hai nhãn khác nhau dùng cùng một vector lượng tử trong 182 hàng này. Chưa có bằng chứng phải đổi kiến trúc hoặc thêm đặc trưng chỉ để phân biệt chính bộ này.

## Kết quả thực đo ngoại tuyến

AI accuracy 130/182 = 71,43%; macro-F1 0,710509; FPR 26/78 = 33,33%. Confusion matrix (hàng nhãn thật; cột Normal/SYN/Scan):

```text
52 26  0
 0 52  0
25  1 26
```

Luật ngưỡng v1 đúng 156/182 = 85,71%, FPR cũng 33,33%; hơn AI ở toàn bộ phiên quét chậm. Chưa chứng minh lợi thế AI.

| Phiên | Raw median: packets, mean IP bytes, SYN q127, src, dst, ports | Kết quả AI |
|---|---|---|
| normal_large | 16, 136, 15, 1, 1, 1 | 26/26 đúng |
| normal_two | 79, 202, 16, 2, 1, 1 | 26/26 đúng |
| normal_retry | 16, 65, 71, 2, 1, 2 | 26/26 nhầm SYN |
| syn_low | 28, 48, 95, 2, 1, 1 | 26/26 đúng |
| syn_high | 153.5, 41, 121, 2, 1, 1 | 26/26 đúng |
| scan_slow | 13, 58, 58, 2, 1, 6 | 25 normal, 1 SYN |
| scan_fast | 122.5, 41.5, 119, 2, 1, 115.5 | 26/26 đúng |

Median là thống kê mô tả, không phải một cửa sổ thực hoặc thông số để gán nhãn lại.

## Nguyên nhân và giới hạn

normal_retry là đối chứng được chủ động gán nhãn bình thường: cùng một dịch vụ không sẵn sàng, một cổng 1884, khoảng 8 lần thử/giây, đồng thời có MQTT trên 1883. SYN cao không tự xác định đó là flood. Model chưa được huấn luyện đủ các hành vi tương tự. Không đổi nhãn thành tấn công để tăng accuracy.

Quét chậm chỉ có 5–6 cổng đích/giây, khác miền tốc độ của bộ gốc. v1 chia số cổng cho 4: 2 -> 0, 5–6 -> 1. Điều này làm biểu diễn các số nhỏ thô hơn; chưa thể quy toàn bộ lỗi cho lượng tử hóa vì mô hình float và phép ablation không có trong gói. Giả thuyết chính là dữ liệu phát triển thiếu điều kiện, kết hợp biểu diễn số cổng chưa phù hợp với quét chậm.

Trong syn_low, SyncookiesSent tăng 281; syn_high tăng 9549. syn_high bắt đầu với 55 SYN_RECV; scan_slow cũng bắt đầu với 55. Có trạng thái TCP còn từ phiên trước vì dùng lại namespace. Không dùng các trạng thái tồn dư để khẳng định quét chậm làm nghẽn server. V2 tạo lại đúng lab thuộc bộ mã trước mỗi phiên.

source.log: SYN low 590 gói/29.508 s, SYN high 9780/29.548 s, scan slow 148/29.622 s, scan fast 5846/29.504 s. Đây là số phát trung bình, không phải ingress PPS mỗi cửa sổ. Một số cửa sổ burst vượt mức yêu cầu do lập lịch bù sau khi VM tạm dừng; bộ phát mới bỏ cơ chế bù, ưu tiên mức trần thay vì cố đạt đủ gói.

Không có phép đo FPGA, chặn gói hoặc bằng chứng gián đoạn dịch vụ trong gói này. Các ảnh MQTT báo thao tác hoàn tất thành công. SYN cookies của Linux có thể giúp dịch vụ tiếp tục hoạt động.

## Quyết định cho v2

Giữ raw features, cửa sổ 1 giây, exact counts và kiến trúc 6–8–3. Chọn divisors cố định [8,2,1,1,1,1] trước thu dữ liệu mới; số cổng nhỏ được giữ nguyên, số lớn hơn 127 chủ động bão hòa. Thu train/val mới, có đối chứng retry, quét chậm và nhiều mức tải. Chọn seed bằng macro-F1 số nguyên trên validation, đóng băng model và baseline rồi mới thu holdout riêng. Không tuyên bố đã đạt 95% trước kết quả holdout.

V2 vẫn phân loại cửa sổ toàn mạng trong lab, chưa định danh nguồn tấn công một cách đầy đủ. Firmware/bộ lọc phải có cơ chế chọn IP và chính sách tránh chặn người dùng hợp lệ. Hành vi benign và ác ý có thể có cùng thống kê; sáu đặc trưng không thể bảo đảm phân biệt mọi trường hợp. Chưa đánh giá IoT-23, mạng thực địa, quét cực chậm dưới phạm vi đã thiết kế hoặc nhiều dịch vụ bình thường thay đổi cổng.
