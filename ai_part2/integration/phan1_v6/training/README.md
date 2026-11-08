# Tái tạo V6 (không bắt buộc để dùng gói)

Bản đã tích hợp có sẵn. Không cần train lại trước khi bàn giao. Các lệnh bên dưới tạo thư mục ứng viên mới, không tự sửa model/core/firmware đang dùng.

`cache/native_patterns.sqlite` giữ nguyên số mẫu/nhãn gốc của 28 Normal IoT-23 + SYN34 + scan Chris Sanders; `cache/v5_patterns.sqlite` bổ sung các biến thể thời gian scan đã có ở V5. Cache lưu các q duy nhất cùng số lần xuất hiện, không phải PCAP tái dựng. Danh sách 30 nguồn/checksum có trong `cache/V5_STATE.json` và `../AI_TRAINING_PROVENANCE.json`. Không đóng gói lại hàng chục GB dữ liệu gốc.

`sources/` có đúng PCAP đã lọc của SYN34, Normal34 và mẫu Chris Sanders. Từ đó `prepare_data.py` tạo 120 profile có PCAP và CSV sáu đặc trưng. Bytes gói tấn công giữ nguyên; đổi thời gian để phủ các mức tải. Trộn mẫu SYN có phản hồi SYN-ACK và ACK thuộc nhãn NativeBenign từ Normal34, đổi địa chỉ/cổng và tính lại checksum. CSV có số gói tấn công/nền và trạng thái từng cửa sổ. Đây là biến thể mô phỏng có kiểm soát, không phải 120 phiên thu mạng độc lập.

SYN train dùng 12.000 gói đầu, development dùng 12.000 gói tiếp theo cùng đợt. Scan dùng cùng nguồn với các hệ số thời gian khác nhau. Cửa sổ SYN dưới20gói tấn công, scan dưới3cổng tấn công được giữ là cần ngữ cảnh, không đổi thành Normal. Cửa sổ dẫn xuất trùng q với nhãn gốc khác được đánh dấu xung đột và không fit/selection; mọi nhãn gốc giữ nguyên. Ma trận tất cả trạng thái có trong `frozen/metrics.json`, gồm cả các hàng này.

Sau khi cài dependencies vào venv riêng (xem `LIBRARY_VERSIONS.json` và `requirements-reproduce.txt`; không thay môi trường đang dùng của bạn):

```bash
cd ~/Downloads/ghep_phan1_ai_v6
~/ai_part2/.venv/bin/python training/test_data.py
~/ai_part2/.venv/bin/python training/prepare_data.py --output ~/iot23_v6_data_tai_tao_01
~/ai_part2/.venv/bin/python training/train.py --output ~/iot23_v6_train_tai_tao_01
```

Đường dẫn Python ví dụ dùng venv của bạn nếu đã có NumPy/scipy/sklearn/Scapy/threadpoolctl. Khác phiên bản thư viện có thể cho trọng số khác. Tại môi trường ghi trong báo cáo, lệnh train mặc định alpha=.01 seed5 đã tái tạo đúng SHA256 model đã giao. `--search` lặp đủ27ứng viên float (mỗi ứng viên40lựa chọn lượng tử hóa) và chọn theo development; có thể chạy lâu. Fit cân bằng các q duy nhất giữa lớp, có lặp điểm nhưng không thêm phiên lưu lượng mới. 36 vector kiểm phản ứng không được đưa vào train.

Các CSV Zeek flow ban đầu phục vụ lọc/nhãn; không phải CSV 6đặc trưng. Model này dùng CSV đặc trưng đã trích theo receiver/cửa sổ. `historical_lab_regression.json` chỉ là kiểm lại lab cũ, không tham gia train hay lựa chọn model; có1Normal nhậnScan. Một trường hợp development SYN803gói bị bỏ sót vẫn giữ trong metrics. Không gọi độ khớp train/development là tỷ lệ phát hiện thực tế.

Nếu đổi model: tạo ứng viên riêng, xuất lại RTL/header/vector, build lại firmware, lặp kiểm số học/CPU/full/system, rồi thu kiểm thử độc lập. Không chép một `model.json` mới vào gói cũ và dùng firmware cũ.
