# Kiểm tra model V4 đã train trên máy của bạn

Model này được giữ nguyên từ tệp bạn gửi, không train lại.
SHA256: `51050d9c05fbbbdda6cca1e21f26366ffcfeddbe7e3a01479a38eb70e790d906`.
Đây là trọng số đã học từ ba thư mục trên máy bạn; khác bản model tham chiếu
của gói train trước. Khi ghép, dùng core, header và model của cùng bộ checksum.

## Xem báo cáo chính xác

Tải [kiem_tra_model_v4.zip](https://github.com/nhudaohaidang-glitch/DoanHTS/blob/ai-part2-starter-20261029/kiem_tra_model_v4.zip), bấm **Download raw**, giải nén trong Downloads của Ubuntu.

```bash
xdg-open ~/Downloads/kiem_tra_model_v4/MO_KET_QUA_V4_CHINH_XAC.html
```

Gói chứa báo cáo đọc được ngay, hai JSON gốc, danh sách cửa sổ cần kiểm tra,
probe ngoại tuyến và project Gowin tái sinh từ đúng model bạn gửi. Đây là
gói kiểm tra; không ghi đè thư mục train, không thay trọng số hoặc nhãn.

## Kết quả theo nhãn của tập học

| Lớp | Đúng | Sai |
|---|---:|---:|
| Normal | 39.253.923 / 39.253.935 | 12, đều dự đoán SYN |
| SYN flood | 21 / 21 | 0 |
| Vertical scan | 4 / 4 | 0 |

Accuracy tập học: **99,99996943%**. Bảng cũ chỉ hiển thị hai chữ số thập phân,
nên làm tròn thành 100,00%. Ma trận float/integer được báo cáo giống nhau;
chỉ mô hình số nguyên được chạy lại ở lần kiểm tra này vì không nhận được
`float_model.json` và toàn bộ CSV đặc trưng từ máy bạn.

Số cửa sổ được dự đoán SYN là 33: 21 mang nhãn SYN, 12 mang nhãn Normal.
Precision SYN theo nhãn đang dùng là **63,64%**. Các số này chưa phải kết quả
trên tập test độc lập. Các cửa sổ Normal được tạo theo từng IP đích /32;
39 triệu cửa sổ không phải 39 triệu phiên mạng độc lập.

## Vấn đề nhãn cần kiểm tra

Đầu vào q `[127,20,127,1,1,1]` xuất hiện ở cả 11 cửa sổ Normal và 21 cửa sổ
SYN. Một model nhận cùng sáu giá trị này phải trả cùng kết quả. Giữ nguyên
nhãn và đầu vào thì ít nhất một phía bị sai; trong model hiện tại là 11 Normal.

Có thêm một cửa sổ Normal với raw `[878,40,127,1,1,1]`, q
`[109,20,127,1,1,1]`, cũng bị nhận SYN. Mẫu thứ 12 không trùng q với điểm SYN
ở trên, nên không gộp nó vào lỗi xung đột nhãn.

Cả 12 trường hợp thuộc capture34, các đích 1.1.1.1 và 50.50.50.53.
`CUA_SO_CAN_RA_SOAT.csv` ghi thời gian, đích, raw, q và scores. Đã tái hiện
đúng số lỗi và ma trận của nguồn capture34 bằng bản đặc trưng cùng nguồn
gốc đang có ở đây. Không tái tính toàn bộ 39 triệu cửa sổ của máy bạn.

Các trường hợp trên là sai **so với nhãn Normal được cung cấp**. Hành vi thực
tế cần đối chiếu PCAP và chú giải nguồn, đặc biệt các đợt SYN dày; chưa tự
đổi nhãn thành tấn công hoặc loại chúng khỏi dữ liệu để tăng điểm.

## Kiểm tình huống và số học

- Hash model khớp `model_sha256` trong metrics. Các ma trận từng nguồn cộng
  lại khớp ma trận tổng, số cửa sổ và các chỉ số báo cáo.
- Dữ liệu đã thấy: 1.513 điểm q Normal phân biệt, 1 SYN và 4 scan. Toàn bộ
  các điểm đó được đưa vào fit; cân bằng bằng lặp tạo 4.539 hàng, không phải
  thêm các phiên tấn công độc lập.
- Cấu trúc đúng 6–8–3, 83 tham số; divisors `[8,2,1,1,1,1]`; shift1=8,
  shift2=2; cận accumulator int32 hợp lệ.
- Python scalar độc lập khớp bản vector hóa trên 1.069 vector số học.
- Icarus RTL khớp 1.069 vector, 84 chu kỳ. Đây là bộ vector bổ sung tại đây,
  khác 1.782 vector mà máy bạn báo đã chạy. Không xác minh lại nguyên vẹn
  bộ 1.782 vector vì bạn chưa gửi tệp vectors của lần train đó.
- Header C v4 biên dịch/liên kết RV32I/ILP32 freestanding thành công, chưa
  thực thi C trên CPU thật hoặc đo timing trên bo.
- Probe một SYN hợp lệ, cảm biến thưa và ACK đơn giản được nhận Normal.
- Trong các vector được dựng cho một nguồn quét một đích, mỗi cổng một SYN,
  IP length 40: 3–17 cổng/giây bị nhận Normal; 18–30 cổng/giây được nhận scan.
  Đây là kết quả của những vector cụ thể, không phải ngưỡng phổ quát của model.

Các probe chỉ để kiểm phản ứng/giới hạn, không phải PCAP thật hoặc tập test
độc lập và không được tự đưa vào train sau khi xem kết quả. Bộ scan học hiện
chỉ có bốn cửa sổ từ một đợt quét nhanh nên chưa bao phủ quét chậm.

## Bước tiếp theo

1. Đối chiếu 12 cửa sổ trong CSV với PCAP và nhãn gốc để quyết định nhãn có
   phù hợp mục tiêu hệ thống hay không. Giữ bản dữ liệu/model hiện tại làm mốc.
2. Thu thêm các phiên lab đã kiểm soát: scan chậm/nhanh, SYN ở nhiều tốc độ,
   và các kết nối bình thường thưa/dày; chia theo phiên và chốt trước khi học.
3. Sau khi chốt model, đánh giá trên phiên mới chưa dùng để chỉnh model.
   CPU vẫn cần chính sách xác nhận nguồn, whitelist và TTL trước khi chặn.

Model hiện được giữ là ứng viên cần rà soát nhãn và kiểm thử thêm, chưa dùng
class_id đơn lẻ để điều khiển chặn tự động.
