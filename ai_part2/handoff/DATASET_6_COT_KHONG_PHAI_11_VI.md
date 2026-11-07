# Giữ core sáu đặc trưng và đọc dữ liệu IoT-23

Core6–8–3 hiện chỉ nhận sáu đặc trưng có ngữ nghĩa đã chốt. Bảng11 đặc trưng đã mã hóa/chuẩn hóa không được đưa trực tiếp vào core, cũng không cắt ngẫu nhiên sáu cột. Cùng số cột nhưng khác đơn vị mỗi hàng, hướng thống kê, cách chuẩn hóa hoặc định nghĩa từng cột vẫn là sai đầu vào.

Trong ảnh bảng11cột, tên trường giống thống kê Zeek theo luồng. Không thấy IP nguồn/đích, timestamp và TCP flags để tính lại chính xác số IP phân biệt, cửa sổ một giây và tỷ lệ SYN mở. Ngay cả khi có scaler để đổi các số về giá trị gốc, những thông tin đã bỏ vẫn chưa tự khôi phục được.

Đường đi đúng với thiết kế hiện tại:

```text
PCAP IoT-23 gốc
  -> IPv4 hợp lệ hướng tới IP bảo vệ
  -> cửa sổ đầy đủ một giây
  -> số gói, độ dài IPv4 trung bình, tỷ lệ SYN mở,
     số IP nguồn, số IP đích, số cổng đích
  -> sáu cột X_raw
  -> chia/clip đúng [8,2,1,1,1,1]
  -> sáu byte q0..q5 -> feat48bit -> core AI
```

Nhãn nằm riêng trong y, không đưa nhãn vào sáu đầu vào. Metadata nguồn/thời gian cũng để riêng. Không dùng 0/1/2 của dataset người khác trước khi xác minh mapping.

## Gói có sẵn dữ liệu để tải

Tệp `iot23_6_dac_trung.zip` ở gốc nhánh chứa **dữ liệu thật**, không chỉ chương trình tải. Giải nén rồi mở `MO_DE_DOC.html` để đọc tiếng Việt. Chứa:

- PCAP Philips Hue4 gốc đầy đủ và log gốc.
- Đoạn PCAP native SYN capture34 đã xác minh:40.568 bản ghi gói, sao chép nguyên byte/timestamp và có đầy đủ nguồn/filter/checksum.
- Log gốc capture34 để đối chiếu; không gán toàn bộ log đó là SYN.
- X_6_raw.csv và X_6_fpga.csv: mỗi tệp đúng sáu cột, tổng2.901 dòng.
- y.csv và metadata nguồn/thời gian để riêng.
- Script và mã trích xuất để tái tạo các CSV từ PCAP đi kèm.

Hai nguồn gồm2.880 cửa sổ Normal và21 cửa sổ của một đoạn SYN. **Không phải toàn bộ IoT-23 hoặc bộ train ba lớp hoàn chỉnh.** Vertical scan của dự án vẫn lấy từ lab; không đổi nhãn quét ngang thành quét dọc. Các nguồn này đã dùng development v3, nên không gọi đây là test độc lập mới;21 cửa sổ SYN không phải21 đợt độc lập.

Đã kiểm: input có đúng sáu cột; mọi giá trị raw khớp cache native trước đây của v3; q khớp chia/clip; nhãn0/1 có mapping/nguồn; bản cắt SYN có40.568 gói và vẫn tạo đúng21 cửa sổ. Model/Verilog/headers được giữ nguyên. Việc đọc/chuyển dataset này không khắc phục các lỗi phân loại đã biết của model.

Tạo lại bảng (tùy chọn, môi trường AI Ubuntu hiện tại đã có NumPy/Scapy):

```bash
cd ~/Downloads/iot23_6_dac_trung
~/ai_part2/.venv/bin/python TAO_LAI_6_COT.py --output ket_qua_tao_lai
```

Để đọc ngay không cần chạy Python: mở HTML hoặc X_6_raw.csv. Tên cột tiếng Anh giữ ổn định cho chương trình, phần giải thích trên HTML là tiếng Việt.
