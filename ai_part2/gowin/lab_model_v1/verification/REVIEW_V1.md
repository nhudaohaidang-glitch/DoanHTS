# Kiểm tra gói mô hình người dùng

Model JSON SHA256 b67f6de6b847a4d2500e2af130c9e31091c92a9cbd3f68de84fe0a31d2a59007.
48 trọng số lớp ẩn, 24 trọng số output, 8 bias ẩn và 3 bias output khớp HEX. Các shift nhất quán với weight_fraction_bits=[4,4], hidden_scale=32, score_scale=128. Đã kiểm tra cận accumulator int32.

Không có PCAP hoặc feature CSV trong gói, nên không tính lại nhãn/đặc trưng/accuracy từ packet. Accuracy là báo cáo từ metrics.json và ảnh người dùng. Metadata có 18 capture/hash khác nhau: 6 train/6 val/6 test, mỗi capture 16 cửa sổ; mỗi split 32 cửa sổ/lớp, distinct=exact. Khác hash không loại trừ mẫu lưu lượng tương tự giữa các phiên.

Float, integer, baseline đều accuracy=1, macro-F1=1, FPR=0 trên test. Baseline có packet_threshold=1, port_threshold=2, syn_ratio_q127_threshold=32. Chưa có bằng chứng AI hơn baseline trên tập này.

Divisors=[8,1,1,1,1,4], shift1=6, shift2=2. Đầu vào bão hòa q0 từ 1024 gói/cửa sổ, q1 từ mean_ip_len=128 byte, q5 từ 512 cổng. Không có CSV để đo tỷ lệ bão hòa thực tế; khi đổi tải/loại dịch vụ cần đánh giá thêm.

Tái tính 360 vector và tái biên dịch RTL gốc/nhúng ROM bằng Icarus; không thực thi sim.vvp tải lên. 84 chu kỳ là latency lõi, không phải độ trễ phát hiện/chặn toàn hệ thống. Gói xuất project là kết quả chuẩn bị; chưa chạy Gowin hoặc kit trong cloud.
