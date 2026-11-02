# Mã tái lập bảng sáu đặc trưng

Gói dữ liệu đầy đủ cho ví dụ này nằm trong `iot23_6_dac_trung.zip` ở gốc nhánh. Các PCAP/SOURCES.json nằm trong gói, không nhân đôi dữ liệu raw trong thư mục mã nguồn này.

Sau giải nén, chạy script TAO_LAI_6_COT.py ngay trong thư mục gói theo README của nó. Script sử dụng bản sao đúng mã part2/features.py đi kèm và tạo lại X sáu cột, y và metadata, không train hoặc sửa model.

trich_syn34.py là helper tạo lại PCAP đoạn SYN từ đúng PCAP capture34 gốc có hash đã ghi. Nó giữ nguyên byte/timestamp của các gói được chọn. Lớp vertical scan không nằm trong bộ đọc hai nguồn này.
