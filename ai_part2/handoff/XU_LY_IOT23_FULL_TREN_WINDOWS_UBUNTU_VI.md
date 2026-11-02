# Xử lý iot_23_datasets_full.tar.gz đang ở Windows

File .tar.gz là nhiều tệp được gom bằng tar và nén gzip, chưa phải một bảng đưa vào AI. Giữ nguyên archive gốc trên Windows. Cách dưới đây cho Ubuntu đọc nó qua VirtualBox, kiểm kê mọi thành viên và chỉ trích các nguồn đã xác minh để tạo đúng sáu đặc trưng. Không cần chép thêm20 GB vào ổ ảo, không bung toàn bộ và không train lại model.

## 1. Chia sẻ thư mục từ Windows cho Ubuntu

Trong cửa sổ VirtualBox đang chạy Ubuntu:

1. Chọn Devices > Shared Folders > Shared Folders Settings.
2. Bấm biểu tượng thư mục có dấu cộng.
3. Folder Path: chọn đúng thư mục Windows đang chứa iot_23_datasets_full.tar.gz.
4. Folder Name: đặt chính xác IoT23.
5. Tích Auto-mount, Make Permanent nếu có, và Read-only để giữ archive gốc.
6. Bấm OK.

Trong Terminal Ubuntu kiểm tra:

```bash
ls -lh /media/sf_IoT23/iot_23_datasets_full.tar.gz
df -h "$HOME"
```

Nếu lệnh đầu không tìm thấy file hoặc báo Permission denied, gửi đúng thông báo để xử lý thư mục chia sẻ trước. Chưa cần cài lại Ubuntu hoặc giải nén toàn bộ. Thư mục chia sẻ cần Guest Additions và quyền đọc phù hợp; không đoán rằng nó đã có trên mọi máy.

## 2. Tải công cụ nhỏ, không tải lại dataset

Tải xu_ly_iot23_full.zip ở gốc nhánh ai-part2-starter-20261029 bằng Download raw, giải nén trong Downloads của Ubuntu thành xu_ly_iot23_full.

Dùng môi trường AI ~/ai_part2/.venv đã có NumPy và Scapy. Công cụ không cần cài thêm thư viện nếu dùng đúng môi trường đó. Dự trù khoảng1 GB dung lượng trống cho lựa chọn mặc định; chương trình cũng kiểm dung lượng đầu ra. Dữ liệu không được nạp toàn bộ vào RAM.

## 3. Đọc archive và tạo sáu đặc trưng

```bash
~/ai_part2/.venv/bin/python ~/Downloads/xu_ly_iot23_full/XU_LY_IOT23.py \
  --archive /media/sf_IoT23/iot_23_datasets_full.tar.gz \
  --output ~/iot23_work_01
```

Đầu ra phải là thư mục mới. Nếu chạy lại sau một lần gián đoạn, dùng tên mới, chẳng hạn iot23_work_02; không xóa archive gốc. gzip phải đọc tuần tự nên dù chỉ giữ một số tệp, chương trình vẫn có thể cần đọc qua toàn bộ21 GB nén. Việc này có thể mất nhiều phút hoặc lâu hơn tùy ổ đĩa/CPU/thư mục chia sẻ; có tiến độ theo dung lượng nén mỗi khoảng10 giây.

Lựa chọn mặc định là Hue4 bình thường và capture34 chứa đoạn SYN đã được xác minh. Theo các snapshot đã dùng trước đây, kết quả dự kiến2880+21=2901 cửa sổ. Chương trình chỉ tạo nhãn nếu PCAP khớp đúng kích thước/hash đã kiểm tra và các điều kiện cửa sổ. Nếu bản archive khác, dữ liệu được ghi nhận trong báo cáo để xem xét; không tự đổi mọi nhãn DDoS/scan sang ba lớp dự án.

Công cụ dùng stream, không extractall. Nó chỉ lưu PCAP được chọn và README/log liên quan; ghi danh sách các tệp khác vào kiểm kê. Không giải nén file chương trình/mẫu mã độc chỉ vì chúng có trong archive. Không chạy tệp lấy ra từ dataset.

## 4. Mở kết quả

Khi hiện DONE:

```bash
firefox ~/iot23_work_01/MO_KET_QUA.html
```

| Tệp | Nội dung |
|---|---|
| KIEM_KE.csv | Đường dẫn, loại và dung lượng các thành viên archive; không phải dữ liệu huấn luyện |
| BAO_CAO.json | Hash archive ghi nhận tại chỗ, nguồn tìm được, kết quả kiểm tra, số cửa sổ |
| raw/ | Chỉ PCAP đã chọn; không phải toàn bộ dataset |
| notes/ | README/log liên quan nếu có trong archive |
| du_lieu_6_cot/X_6_raw.csv | Đúng sáu đặc trưng thô mỗi giây |
| du_lieu_6_cot/X_6_fpga.csv | Sáu q sau chia/clip đúng divisor v3 |
| du_lieu_6_cot/y.csv | Nhãn riêng, không đưa vào sáu đầu vào |
| du_lieu_6_cot/THONG_TIN_DONG.csv | Nguồn/thời gian của từng dòng, không đưa vào model |

Bạn gửi BAO_CAO.json và X_6_raw.csv để kiểm tra bước tiếp, không cần gửi archive20 GB. Nếu ERROR trước DONE, gửi nguyên lỗi; nếu đã có BAO_CAO.json và KIEM_KE.csv thì kèm chúng. Đừng tự đổi tên nhãn, hash hoặc xóa những dòng không hợp ý.

## 5. Giới hạn của bước này

Đây là bước đọc/kiểm kê và tái lập các nguồn native đã dùng trong development v3, không phải train mới hay test độc lập. Các nguồn mặc định chỉ có0=Normal và1=đoạn SYN;2=vertical scan tiếp tục lấy từ lab có kiểm soát. Những capture khác trong toàn bộ IoT-23 có nhiều nhãn và loại lưu lượng khác; phải kiểm tra trước khi chọn vào bài toán ba lớp.

Giữ nguyên core sáu đặc trưng và model v3 hiện tại. Không lấy sáu cột tùy ý từ bảng11 đặc trưng chuẩn hóa theo flow. Một dòng PCAP là một gói; một dòng Zeek log là một luồng; một dòng X ở đây là một cửa sổ đầy đủ một giây hướng tới IP được bảo vệ.

Ngữ nghĩa sáu cột: packet_count, mean_ip_bytes, syn_ratio_q127, src_count, dst_count, dst_port_count. q=clip(raw//[8,2,1,1,1,1],0,127), N=0 skip; không dùng q0=0 làm điều kiện bỏ cửa sổ.

Chương trình đã được kiểm tra bằng các archive mẫu chứa đúng PCAP đã xác minh, gồm PCAP thường và xz, so sáu đặc trưng với cache v3, kiểm tra hash/đường dẫn và không gắn nhãn cho phiên bản chưa xác minh. Chưa chạy trên chính archive20 GB ở máy người dùng. Bố cục header đầu archive chính thức đã được kiểm tra từ máy chủ công bố; hash từng PCAP vẫn là bước xác nhận ở máy người dùng.
