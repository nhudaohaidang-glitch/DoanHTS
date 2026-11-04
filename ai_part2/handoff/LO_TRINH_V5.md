# Dùng đúng ba nhóm dữ liệu đã tạo, đi từ train đến ghép

V5 đã train từ cache PCAP Normal IoT-23, SYN flood capture 34 và vertical
scan Chris Sanders, cộng các biến thể thời gian của cùng PCAP scan. CSV
flow giữ nhãn và thông tin lọc. Mạng AI học **sáu đặc trưng mỗi giây** trích
từ PCAP; không đưa thẳng các cột CSV flow vào mạng. Không thêm nguồn lab
MQTT vào tập học trong gói này.

Có thể bắt đầu thử ghép core V5 ngay. Để kết luận firewall hoạt động đúng
cần kiểm cả bộ trích đặc trưng, CPU, đường Ethernet và bo thật. Train lại
nhiều lần trên các tệp cũ không thay thế những phép kiểm này.

## 1. Chuẩn bị tệp bàn giao trên Ubuntu

Tải `v5_san_sang_ghep.zip`, bấm Download raw, giải nén vào Downloads thành
`~/Downloads/v5_san_sang_ghep`. Giữ `~/iot23_da_loc_01` và môi trường Python
`~/ai_part2/.venv` đang có. Chạy không sudo:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/v5_san_sang_ghep/BAT_DAU_V5.py
```

Lệnh chỉ đọc model/cache và dữ liệu gốc, kiểm đủ 30 PCAP được chọn, đối
chiếu lại ma trận V4/V5 từ cache và xuất tệp ghép vào `~/iot23_v5_ghep_01`.
Chưa đọc lại checksum của toàn bộ các PCAP lớn ở chế độ mặc định. Không fit,
không đổi nhãn và không thay core trong project của người khác.

Mở kết quả:

```bash
xdg-open ~/iot23_v5_ghep_01/MO_BAN_GIAO_V5.html
```

Nếu đã có thư mục đầu ra, giữ nguyên và dùng tên khác:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/v5_san_sang_ghep/BAT_DAU_V5.py \
  --output ~/iot23_v5_ghep_02
```

Nếu thư mục dữ liệu khác, truyền `--data /duong/dan/thu_muc_chua_ba_nhom`.
Có thể thêm `--verify-pcaps` để đọc và đối chiếu SHA256 cả 30 PCAP; bước này
mất thời gian đọc dữ liệu nhưng không giải nén lưu thêm ra đĩa.

## 2. Kiểm lại core trên máy bạn

```bash
bash ~/iot23_v5_ghep_01/gowin/verification/run_sim.sh
```

Mong đợi `PASS vectors=1896 cycles_min=84 cycles_max=84`. Cần Icarus
(`iverilog`, `vvp`) đã dùng khi train V4. Nếu thiếu, giữ thông báo để cài đúng
công cụ trước khi gọi bước này đạt. Kiểm này bao gồm reset giữa phép tính,
start lúc busy, chốt feat, độ dài done và scores giữ ổn định. PASS chứng
minh số học core khớp model; không phải 100% phát hiện tấn công.

## 3. Mở core trong Gowin trên Windows

Trên Windows, tải và giải nén cùng gói ZIP rồi mở
`candidate_v5/gowin/ai_core_v5.gprj`. Chạy **Synthesize** cho core V5, lưu
báo cáo tài nguyên và cảnh báo. Kết quả synthesis của V1/V3 không được dùng
thay cho V5. Khi ghép top, chốt clock/constraints thực tế và kiểm timing
sau place-and-route. Project core riêng chưa có toàn bộ chân/cổng Ethernet.

## 4. Bàn giao đúng người, đúng tệp

| Người | Tệp trong `~/iot23_v5_ghep_01` | Việc cần đạt |
| --- | --- | --- |
| Bạn — AI | model/, READY_REPORT.json, vector và báo cáo | Giữ model/hash, giải thích đặc trưng/giới hạn, đối chiếu kết quả |
| Người 1 — CPU/top | gowin/src/ai_core_model_v5.v, firmware/, ai_v5_handoff_vectors.h | Driver thật cấp đúng 48 bit, start/busy/done, đọc đúng scores/class |
| Người 3 — feat_core | FEATURES_V5.md, INTEGRATION_V5.csv | Cùng gói và mốc cửa sổ thì raw/q/feat giống Python |
| Người 4 — MAC/Ethernet | Kết quả kiểm đường dữ liệu của nhóm | Frame thật đi qua FPGA, CRC/FIFO/clock và chiều bridge đúng |

Chỉ để một định nghĩa module `ai_core` trong top. Header C, RTL nhúng ROM
và model phải cùng SHA phiên bản. Người 1 dùng map thanh ghi thật của nhóm;
gói AI không tự quy định địa chỉ MMIO mới.

Với 36 vector có gói, CPU phải đọc đúng từng score int16 có dấu và class.
Với hàng `empty_skip`, CPU không phát start. Các cửa sổ 1–7 gói vẫn phải
được xử lý dù q0=0. Sau đó dùng cùng một đoạn PCAP, cùng đích /32 và cùng
mốc 1 giây để đối chiếu raw counters giữa Python và `feat_core`.

## 5. Thử toàn hệ thống bằng lab MQTT đang có

Trước hết xác nhận các gói lab thực sự đi qua FPGA và bộ thống kê đúng
chiều; lab namespace chạy trong Ubuntu chưa tự có nghĩa đường gói đã qua
bo. Người làm MAC/top xác nhận đường Ethernet này.

Lần lượt quan sát Normal, SYN và scan, ghi theo từng giây: model/hash,
đích/cửa sổ, packet_count, tổng IPv4 bytes, số SYN mở, ba số đếm phân biệt,
q/feat, scores và class_id. Đối chiếu các tầng theo FEATURES_V5.md. Thử
chuyển tiếp ARP/hai chiều và luật lọc cố định trước khi nối quyết định AI
vào luật CPU. Cuối cùng đo MQTT gửi/nhận, chặn nhầm, lượng lọt qua trước
khi chặn, timeout/TTL và xử lý reset/overflow theo thiết kế nhóm.

Lab dùng để kiểm ghép và đo trên hệ thống; các PCAP học gốc vẫn giữ nguyên.
Thử lại chính dữ liệu đã học là kiểm tái lập, không gọi là test độc lập.

## 6. Khi nào cần train lại?

Hiện tại không cần chạy fit thêm để tạo core: V5 đã có trọng số và đã xuất
RTL. Vẫn còn 12 cửa sổ Normal bị nhận SYN; 11 cửa sổ có q giống 21 cửa sổ
SYN, và có raw trùng giữa hai nhãn. Không thể học ra hai đáp án khác nhau
cho cùng đầu vào bằng tăng số vòng lặp. Giữ nguyên nhãn nguồn để rà soát.

Nếu muốn tự tái lập đúng bước train trên cache ba nhóm đã gửi:

```bash
~/ai_part2/.venv/bin/python ~/Downloads/v5_san_sang_ghep/code/tools/train_from_v4_cache.py \
  --base-v4 ~/Downloads/v5_san_sang_ghep/V4_GOC \
  --output ~/iot23_train_v5_tu_train_01
```

Ứng viên tự train nằm riêng. Phiên bản thư viện khác có thể cho trọng số
khác: xem SHA và report, không chép model mới vào gói đã chốt để dùng lại
RTL/header/vector cũ. Công cụ bàn giao này cố ý chỉ chấp nhận V5 SHA đã kiểm.

Nếu muốn sửa model sau kết quả lab, phải giữ kết quả cũ, xác định dữ liệu
phát triển và phiên kiểm riêng trước khi train ứng viên mới. Không đổi các
phiên đã xem để sửa model thành test chưa từng thấy. Với giới hạn chỉ dùng
ba nguồn hiện có, không thể tự tạo bằng chứng khái quát chỉ bằng fit lại.

## Tiêu chí hoàn tất

- **Đã train:** có model float/integer, nguồn ba nhóm và ma trận đầy đủ — đã đạt.
- **Đã chuẩn bị ghép core:** RTL/header/vector/contract cùng model, mô phỏng đạt — gói này cung cấp; cần chạy và đối chiếu trên project của nhóm.
- **Đã ghép hệ thống:** raw từ feat_core khớp Python; CPU scores/class khớp;
  top synthesis/timing đạt; MQTT qua FPGA và luật lọc hoạt động — cần kết quả của nhóm.
- **Độ tin cậy phân loại:** báo theo từng lớp và nguồn, ghi lỗi/xung đột,
  có thử riêng trước khi tuyên bố khả năng phát hiện trên lưu lượng mới.

Bước tiếp theo cần gửi lại: READY_REPORT.json, log mô phỏng và báo cáo
Synthesis V5. Để hỗ trợ sửa dây nối/driver cụ thể, cần source top,
wrapper/thanh ghi AI và feat_core mà nhóm đang thực sự ghép; thư mục repo
hiện có chưa chứa các module nhóm mới nhất này.
