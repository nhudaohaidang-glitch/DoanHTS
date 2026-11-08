# Sau khi đã tạo sáu đặc trưng IoT-23

Bước tiếp theo là cho model v3 đã chốt chạy dự đoán, so với nhãn thật và xem kết quả riêng Normal/SYN. Hai nguồn Hue4/Syn34 đã dùng phát triển v3: đây là bước tái lập, không phải test độc lập và không cần train lại.

## Chạy trên máy Ubuntu

Tải chay_ai_iot23.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads, để có ~/Downloads/chay_ai_iot23/CHAY_AI.py. Gói chứa đúng model v3 đã chốt và bộ tính số nguyên; không cần đoán đường dẫn model trong bản kit cũ.

```bash
~/ai_part2/.venv/bin/python ~/Downloads/chay_ai_iot23/CHAY_AI.py \
  --data ~/iot23_khoi_phuc_01 \
  --output ~/iot23_du_doan_01
```

Khi hiện DONE:

```bash
firefox ~/iot23_du_doan_01/XEM_DU_DOAN.html
```

Gửi ảnh phần kết quả theo nguồn và bảng nhãn thật/dự đoán. Nếu ERROR, gửi nguyên thông báo; không sửa nhãn hoặc xóa những dòng bị dự đoán sai. Đầu ra phải là thư mục mới; khi cần chạy lại, dùng tên ~/iot23_du_doan_02.

## Đọc kết quả

- X_6_raw.csv: sáu số đặc trưng trích từ PCAP, mỗi dòng là một cửa sổ đầy đủ một giây hướng tới IP bảo vệ và có gói.
- X_6_fpga.csv: sáu q = clip(raw//[8,2,1,1,1,1],0,127). Đây là đầu vào thực sự của phép tính integer; không chia/clip lần nữa. raw packet_count từ1 đến7 có q0=0 vẫn được dự đoán.
- y.csv: nhãn thật giữ riêng, không đưa vào model.0=Normal,1=đoạn SYN đã xác minh; không có mẫu thật lớp2 trong hai nguồn này.
- DU_DOAN.csv ở thư mục mới: mỗi dòng có nguồn/thời gian, nhãn thật, dự đoán, đúng/sai và ba score số nguyên. Score không phải xác suất phần trăm.
- BAO_CAO_DU_DOAN.json: hash model/CSV, số dòng và bảng nhãn thật/dự đoán theo từng nguồn; ghi rõ independent_test=false.

Trang HTML hiển thị vài dòng cả Hue4 và Syn34 để không chỉ nhìn thấy những dòng Normal đầu bảng. Chương trình kiểm đúng cột, số dòng, q khớp raw, số cửa sổ từng nguồn, nhãn theo nguồn và thứ tự thời gian trước khi dự đoán. Không sửa dữ liệu đầu vào hay model.

Model SHA256: e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d. Gói chỉ chấp nhận model này. Nó chạy Python trên CPU theo số học của core; đây chưa phải chạy trên FPGA hoặc kiểm thử chặn Ethernet.

Kiểm tra ở workspace trên các PCAP tham chiếu cho kết quả2880/2880 Normal và21/21 SYN. Nếu máy người dùng cũng cho2901/2901 thì chỉ xác nhận tái lập trên hai nguồn development này. Không dùng con số đó để kết luận v3 đạt100% ngoài thực tế hoặc đã kiểm đủ ba lớp.

Giữ các kết quả lab mới trước đây: v3test01 đúng214/219, còn5 cửa sổ quét chậm bị bỏ sót. Một SYN hợp lệ đơn lẻ cũng có thể bị v3 nhầm thành SYN. Không dùng kết quả tái lập này để bỏ qua các giới hạn đó hoặc tự đổi model rồi tiếp tục gọi bộ test đã xem là độc lập. Phần vertical scan phải xem dữ liệu lab có nhãn đã xác minh, tách riêng kết quả nguồn native và lab.
