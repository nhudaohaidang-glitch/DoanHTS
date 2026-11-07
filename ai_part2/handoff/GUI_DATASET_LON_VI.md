# Gửi nhiều dataset lớn để kiểm tra

## Cách dễ nhất: nén ZIP trước

File CSV 66 MB có nhiều số/text thường nén nhỏ hơn nhiều. Trên Windows, tạo một thư mục `dataset_ban_gui`, chép các dataset và tài liệu liên quan vào đó; nhấp phải thư mục, chọn Compress to ZIP file hoặc Send to > Compressed (zipped) folder. Nếu ZIP nhỏ hơn khoảng 25 MB, đính kèm trực tiếp vào chat. Đây là kích thước khuyến nghị để xử lý thuận tiện, không phải tuyên bố giới hạn chung của mọi giao diện ChatGPT.

Nên kèm tên gốc các tệp và README, code xử lý dữ liệu `.py`/`.ipynb`, bảng đổi tên nhãn dạng JSON/text, thông số chuẩn hóa hoặc dữ liệu trước chuẩn hóa. Giữ riêng tên train/validation/test nếu đã có. Không chỉ gửi ảnh Excel vì ảnh chỉ cho thấy một số hàng, không cho biết toàn bộ giá trị hoặc cách nhãn được tạo.

## Nếu ZIP vẫn lớn: công cụ chia gói độc lập

Tải `cong_cu_gui_dataset.zip` từ gốc nhánh ai-part2-starter-20261029 bằng Download raw. Giải nén trong Downloads thành `cong_cu_gui_dataset`.

Trên Ubuntu, đặt các tệp muốn gửi trong:

```text
~/Downloads/dataset_ban_gui/
```

Chạy:

```bash
python3 ~/Downloads/cong_cu_gui_dataset/dong_goi.py \
  --input ~/Downloads/dataset_ban_gui \
  --output ~/Downloads/dataset_gui_chatgpt
```

Không cần sudo hoặc thư viện bổ sung; dùng Python 3.8 trở lên. Thư mục đầu ra phải chưa tồn tại và nằm ngoài thư mục đầu vào. Nếu chạy lần nữa, đổi tên đầu ra như `dataset_gui_chatgpt_02`.

Nếu dùng Windows đã có Python, cũng có thể chạy trong PowerShell, thay đường dẫn bằng vị trí thật:

```powershell
py "$HOME\Downloads\cong_cu_gui_dataset\dong_goi.py" --input "$HOME\Downloads\dataset_ban_gui" --output "$HOME\Downloads\dataset_gui_chatgpt"
```

Đính kèm **tất cả `GUI_*.zip`** trong thư mục đầu ra vào chat, có thể gửi qua nhiều tin nhắn. Gửi thêm `THONG_TIN_GUI.json` nếu tiện, nhưng mỗi ZIP đã mang đủ thông tin của bản thân nó. Khi gửi xong ghi rõ “đã gửi đủ”.

Chương trình nén trước. Nếu vẫn lớn, nó chia bản nén thành các phần 16 MiB, đặt từng phần trong một ZIP thông thường có thông tin thứ tự và SHA256; mỗi ZIP tối đa 20 MiB. Đây không phải chia CSV theo dòng: khi ghép lại, các tệp gốc được khôi phục đúng từng byte, kể cả CSV/Excel/Parquet. Người nhận cần đủ các phần để khôi phục bản đầy đủ. Không tự ghép nhầm nội dung khác nhau chỉ vì cùng tên GUI_001.zip; metadata chứa hash của bản nén đầy đủ để phân biệt.

Chương trình chỉ đọc các tệp trong thư mục bạn chọn, nén và ghi đầu ra; giữ nguyên dữ liệu gốc. Không tải lên mạng tự động, không huấn luyện model. Bỏ thư mục .git, .venv, venv, __pycache__, node_modules và các tệp symlink. Chọn thư mục chỉ chứa dữ liệu/tài liệu muốn chia sẻ thay vì chọn toàn bộ ổ đĩa hoặc thư mục cá nhân.

## Ảnh dataset mới hiện cho biết gì?

Ảnh có 11 cột đầu vào: id.orig_p, id.resp_p, proto, duration, orig_bytes, resp_bytes, conn_state, orig_pkts, resp_pkts, orig_ip_bytes, resp_ip_bytes; cột thứ 12 là class. Các tên gần với Zeek flow logs. Port, giao thức, trạng thái, số gói trong ảnh đã thành số thập phân, có cả số âm: đây có dấu hiệu đã mã hóa/chuẩn hóa, không phải giá trị mạng thô. Có thể là StandardScaler hoặc cách biến đổi khác; cần code hoặc thông số gốc để xác nhận.

Ví dụ `id.orig_p=-0.9475434` không phải một cổng thật âm. Một cách chuẩn hóa thường gặp là `(giá trị gốc - trung bình) / độ lệch chuẩn`; nhưng không thể khôi phục cổng thật từ số đó nếu chưa biết phép biến đổi và tham số. `proto=-0.08928988` cũng chưa cho biết đó là TCP hay UDP nếu thiếu bảng mã hóa.

Với model v2/v3 của chúng ta, quy ước là0=Normal,1=SYN flood,2=vertical scan. **Không áp quy ước đó cho cột class của bạn gửi khi chưa có bằng chứng mapping.** Dataset khác có thể dùng thứ tự hoặc ý nghĩa khác. Nhãn gốc IoT-23 thường là chuỗi như Benign/Malicious/DDoS/PartOfAHorizontalPortScan, nên số0/1/2 là một bước mã hóa/đổi nhóm của người xử lý.

Bạn có thể gửi người tạo dataset câu sau:

> Trong các file này, class 0, 1, 2 tương ứng chính xác tên nhãn nào? Bạn gửi mình đoạn code gộp/đổi nhãn, danh sách tên lớp, code mã hóa các cột proto/conn_state, cách chuẩn hóa, và cho biết từng file là train/validation/test hay nguồn khác nhau nhé.

Bảng này có 11 đặc trưng theo luồng và đã xử lý, khác sáu đặc trưng theo cửa sổ một giây của core AI hiện tại. Chưa đưa trực tiếp bảng này vào core v3. Muốn đánh giá dùng được thế nào phải xem nguồn, mapping, preprocessing và đơn vị mỗi hàng; không thể tự suy ra chính xác các cửa sổ một giây/SYN ratio/cardinality từ ảnh đã bỏ IP và timestamp.
