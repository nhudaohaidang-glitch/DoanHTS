# Phạm vi kết quả model V6

Model giữ đúng SHA256 `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`. Lần tách gói này không train hoặc sửa trọng số. V6.1 trước đây là thay đổi đường RX/MAC của bản ghép; phần đó không nằm trong gói AI riêng.

Nguồn dữ liệu: Normal IoT-23 (28 PCAP đã chọn), SYN flood capture 34 IoT-23 (một đợt), vertical scan Chris Sanders (một đợt), cùng các biến thể thời gian/nền đã công bố từ các nguồn đó. Gói chính có metrics/provenance; mã train, cache, PCAP và CSV được đóng riêng.

| Nhóm đánh giá | Kết quả và giới hạn |
|---|---|
| Tập gốc | Normal đúng 39.253.923/39.253.935, còn 12 lỗi theo nhãn gốc; SYN đúng 21/21; scan đúng 4/4. Đây là độ khớp tập học. Có 11 Normal trùng q với SYN. Số lỗi bằng V5 nhưng vị trí có thay đổi. |
| Development cùng nguồn | Normal đúng 348/348, SYN đúng 2.355/2.356, scan đúng 640/640. Còn một cửa sổ SYN 803 gói bị bỏ sót. Các hàng thưa hoặc xung đột nhãn được giữ và báo riêng. |
| Lab lịch sử | Đúng 218/219; có một Normal nhận thành scan. Đây là hồi quy lab cũ, không phải kiểm thử độc lập mới. |

3.762 vector RTL và 41 tham chiếu counter kiểm tính toán, giao tiếp và độ trễ. Chúng không phải các phiên lưu lượng độc lập để đo accuracy. Bộ counter có 40 đầu vào hợp lệ và một cửa sổ rỗng; bốn case cuối là ví dụ tổng hợp counter có kiểm soát, không phải capture mới hoặc mẫu train.

Kết quả mô phỏng không xác nhận timing trên bo, PHY, throughput hoặc hiệu quả chặn trên mạng thực. Cần kiểm toàn hệ thống sau khi ghép và đánh giá trên lưu lượng độc lập.
