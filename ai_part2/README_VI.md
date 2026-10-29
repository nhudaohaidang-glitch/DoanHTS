# Người 2 — bộ mã độc lập cho SYN flood và vertical scan

## Bộ này giúp làm được gì?

1. Cài công cụ trong Ubuntu VirtualBox; giữ nguyên Windows, VS Code và Gowin.
2. Tự kiểm tra PCAP -> đặc trưng -> MLP -> trọng số số nguyên -> Verilog, chưa cần kit.
3. Dựng lab MQTT cô lập trong một Ubuntu bằng Linux network namespaces, không cần chờ Ethernet của nhóm.
4. Thu PCAP thật, tạo dữ liệu ba lớp, train và xuất model mới.
5. Chạy dashboard log tối thiểu (Python), chưa cần Node-RED.

KHÔNG bao gồm MAC Ethernet, parser/bộ lọc RTL, firmware PicoRV32 hoặc tự cấu hình iptables chặn từ AI. ai_core phải ghép sau theo hợp đồng với người 1/3. Không có kết quả accuracy mạng thật 95% trong gói này. Dashboard Python là bản tối thiểu thay cho giai đoạn đầu; Node-RED trong PDF có thể làm sau.

## Bước 0 — đưa gói ZIP vào Ubuntu

Dùng Firefox trong Ubuntu tải ZIP từ cuộc trò chuyện, hoặc dùng Shared Folder của VirtualBox để chép ZIP từ Windows. Không làm việc trực tiếp trong Shared Folder; chép về Home trước. Giải nén bằng Files/Archive Manager sao cho có thư mục ~/ai_part2. Nếu thư mục đó đã tồn tại, giữ bản cũ và dùng thư mục mới; không ghi đè file cá nhân.

Mở Terminal (Ctrl+Alt+T):

```bash
cd ~/ai_part2
ls
lsb_release -ds
```

Bạn phải thấy README_VI.md, lab, rtl, scripts, tools. Ubuntu được cấp 4–6GB RAM, 2 CPU và đủ trống ổ đĩa cho PCAP. Không cần GPU. Để card VirtualBox NAT cho tải gói; lab bên dưới không sử dụng card này để phát thử nghiệm.

## Bước 1 — cài phần mềm trong Ubuntu

```bash
cd ~/ai_part2
bash scripts/install_ubuntu.sh
```

Nhập mật khẩu Ubuntu khi sudo hỏi (Terminal không hiện ký tự lúc gõ). Script dùng kho apt có xác minh của Ubuntu, tạo .venv --system-site-packages, không sửa firewall máy chủ, không đổi SYN cookies. Các gói chính: Python/numpy/scikit-learn/Scapy/paho-mqtt/pyserial, Mosquitto, tcpdump, iproute2, iptables và Icarus Verilog. Chưa cần cài thêm Python hay trình mô phỏng trên Windows. Có thể cài extension Python và Verilog trong VS Code về sau; không bắt buộc để chạy lệnh.

Ubuntu 26.04 có Python mới; dùng bản thư viện do apt của chính Ubuntu cung cấp để tránh lỗi wheel cũ. requirements-cloud-tested.txt chỉ ghi lại môi trường Python 3.12 đã kiểm thử ở cloud, KHÔNG ép file đó vào Python 3.14. Nếu apt không tìm thấy một gói, giữ thông báo lỗi; không tắt xác minh hoặc cài script lạ.

## Bước 2 — tự kiểm tra trước, chưa thu dữ liệu lab

```bash
bash scripts/selfcheck.sh
```

Chương trình tạo PCAP NHÂN TẠO, chia theo phiên thành train/val/test, tính sáu đặc trưng, train MLP 6-8-3 và xuất ROM. Nó chạy testbench so khớp điểm số với Python, đồng thời thử reset giữa giao dịch, start khi busy và chốt feat.

Kết quả mong đợi có dòng:

```
PASS vectors=384 cycles_min=84 cycles_max=84
```

Nếu số vector thay đổi khi bạn thay code, phải đối chiếu số thực tế. Xem build/demo_model/metrics.json, build/demo_training.log và build/demo_model/rtl_result.log. Độ chính xác trên PCAP nhân tạo chỉ là kiểm tra pipeline, KHÔNG được đưa vào báo cáo như kết quả phát hiện mạng thật.

Các đầu ra không bị tự ghi đè. Muốn làm lại, đổi tên thư mục build cũ để lưu kết quả rồi chạy script; script sẽ tạo build mới. Có thể bị SKIP bài MQTT integration nếu chưa đặt PART2_MOSQUITTO_BIN; đó là bài tùy chọn được chạy riêng bên dưới.

```bash
PART2_MOSQUITTO_BIN="$(command -v mosquitto)" .venv/bin/python -m unittest discover -s tests -v
```

Bài này mở broker chỉ trên loopback, gửi ba bản tin thật và kiểm tra subscriber nhận đủ. Broker tự dừng sau test; không thay dịch vụ Mosquitto đang chạy trên cổng mặc định.

## Bước 3 — tạo lab gói mạng thật trong một Ubuntu

```bash
sudo bash lab/setup_lab.sh up
sudo ip netns list
```

Kết quả có ba namespace:

```
p2sensor (198.18.0.2) ──┐
                       ├── bridge p2br ── p2broker (198.18.0.1)
p2source (198.18.0.3) ──┘
```

Đây là các network stack Linux có IP riêng, không phải ba máy vật lý. Không có default route/uplink ra Internet. Script chỉ tạo các namespace/veth/bridge đặt tên p2..., và một luật bỏ TCP RST bên trong p2source để kernel không tự hủy các yêu cầu SYN của công cụ thử. Không đổi firewall của Ubuntu host. Nếu tên đã tồn tại, script từ chối ghi đè.

### Thu phiên bình thường đầu tiên

```bash
sudo bash lab/run_capture.sh normal train normal_train01 20
```

Script tự chạy Mosquitto trong p2broker, subscriber ghi dữ liệu, cảm biến cứ 1 giây kết nối/gửi QoS1/ngắt, và tcpdump. Sau khoảng 20 giây nó dừng các tiến trình vừa tạo, in số thành công/thất bại và lưu:

```
data/captures/normal_train01/
  traffic.pcap
  sensor.jsonl
  received.jsonl
  broker.log
  capture.log
```

Mở sensor.jsonl và received.jsonl bằng VS Code. Có sensor ok=true chưa đủ nếu subscriber không nhận; kiểm tra cả hai. capture.log ghi số gói bị kernel bỏ; nếu có mất gói cần xử lý trước khi dùng PCAP làm chuẩn đếm.

### Thu hai kịch bản còn lại

```bash
sudo bash lab/run_capture.sh syn train syn_train01 20
sudo bash lab/run_capture.sh scan train scan_train01 20
```

Nguồn thử chỉ cho chạy trong p2source, đích cố định 198.18.0.1, tối đa 60 giây và 500 gói/giây. Không có tham số nhắm tới máy ngoài. Mặc định SYN vào cổng broker 1883; vertical scan thử nhiều cổng trên cùng máy broker. Kiểm tra source.log và PCAP xác nhận nguồn thực sự đã chạy. PCAP/session được gán nhãn kịch bản, không tự gán nhãn từng gói.

Công cụ cố ý giới hạn tải. Broker có thể vẫn phục vụ bình thường: đây là một kết quả hợp lệ, không phải lý do tắt bảo vệ OS hoặc ép laptop sập. Không được dùng việc có nhãn syn làm bằng chứng dịch vụ đã bị DoS thành công. Thu dữ liệu và đo ảnh hưởng là hai việc khác nhau. Hiệu ứng trên lab namespace cũng chưa chứng minh hành vi trên hai LAN8720 thật.

### Thu validation và test, tách hẳn phiên

```bash
sudo bash lab/run_capture.sh normal val normal_val01 20
sudo bash lab/run_capture.sh syn val syn_val01 20 250
sudo bash lab/run_capture.sh scan val scan_val01 20 80
sudo bash lab/run_capture.sh normal test normal_test01 20 200 0.5
sudo bash lab/run_capture.sh syn test syn_test01 20 150
sudo bash lab/run_capture.sh scan test scan_test01 20 120
```

Đây chỉ là tối thiểu để pipeline chạy đủ ba lớp. Thu thêm nhiều phiên, thay đổi tốc độ/tải và thời điểm; ba phiên mỗi lớp trở lên vẫn chưa tự bảo đảm khái quát. Đừng đổi nhãn để tăng accuracy. Giữ test riêng, không điều chỉnh mô hình theo test rồi báo chính kết quả đó.

Dừng lab khi không dùng:

```bash
sudo bash lab/setup_lab.sh down
```

Lệnh chỉ xóa lab có ownership marker của bộ mã này, không xóa dữ liệu đã thu.

## Bước 4 — tạo đặc trưng từ PCAP thật

```bash
.venv/bin/python tools/feature_quant.py \
  --manifest data/captures/manifest.csv \
  --output build/lab_features.csv
```

start/end trong manifest giới hạn đoạn có nhãn, script capture đã loại khoảng đầu/cuối. Cửa sổ 1 giây, theo epoch, không chồng lấn. Nhãn: 0 bình thường, 1 SYN flood, 2 vertical scan. SHA256 ngăn dùng cùng file trong nhiều phiên/split. Đọc build/lab_features.meta.json để biết số gói bị bỏ qua do fragment/truncated.

Chi tiết sáu đặc trưng trong spec/FEATURES_V0.md. Đây là spec NHÁP phải gửi người 1/3. Nếu RTL đếm bitmap, hãy mô phỏng đúng bitmap trên Python rồi train lại; mode exact mặc định không được mặc định bằng bitmap. Mốc cửa sổ Python và RTL phải căn giống nhau khi đối chiếu.

## Bước 5 — train và xuất model thật

```bash
.venv/bin/python tools/train.py \
  --dataset build/lab_features.csv \
  --output build/lab_model_v1 > build/lab_training.log
```

Đọc build/lab_model_v1/metrics.json:
- float và integer metrics riêng, confusion matrix và recall từng lớp;
- FPR: tỷ lệ cửa sổ bình thường bị báo thành tấn công;
- threshold_baseline: luật ngưỡng so sánh được chọn bằng validation;
- convergence_warning_count: nếu >0, kiểm tra độ hội tụ trước khi kết luận.

Trọng số và bias được lượng tử hóa int8/int32, accumulator kiểm tra cận tràn, hidden ReLU và scores có bão hòa. Input divisors trong model.json chỉ fit trên train. Khối firmware cần dùng đúng divisor/shift này.

Thử một đầu vào (chỉ minh họa, không gán trước kết quả):

```bash
.venv/bin/python tools/predict.py --model build/lab_model_v1/model.json \
  --features 200 40 120 2 1 1
```

## Bước 6 — kiểm tra accelerator Verilog

```bash
bash scripts/run_rtl.sh build/lab_model_v1
```

Icarus compile RTL, nạp ROM rồi chạy vectors.txt. Testbench so TỪNG score và class, không chỉ kiểm tra module chạy xong. $fatal làm lệnh trả lỗi nếu mismatch hoặc timeout. Model mới có số vector khác model demo.

84 chu kỳ là suy luận riêng, không gồm cửa sổ 1 giây, tiền xử lý, firmware, chờ xác nhận hai cửa sổ hay truyền Ethernet. Giả sử sau này thực sự đạt 27MHz, 84 chu kỳ tương đương khoảng 3,11us; hiện chưa có kiểm chứng timing trên kit.

Gowin dùng sau khi simulation đúng: tạo project đúng part in trên kit, thêm rtl/ai_core.v, thêm thư mục chứa quant_params.vh vào include path; ROM .hex phải có đường dẫn hợp lệ (có thể đặt parameter W1_FILE/B1_FILE/W2_FILE/B2_FILE theo đường dẫn trên máy). Chỉ chạy Synthesis riêng để khảo sát tài nguyên. Timing/pin và việc chạy trên board do top tích hợp nhóm kiểm chứng. Không thêm cùng lúc stub ai_core và ai_core thật vào cùng danh sách source.

## Bước 7 — dashboard và log

Tạo log mẫu có checksum thật:

```bash
.venv/bin/python tools/make_sample_log.py > build/sample.log
.venv/bin/python tools/dashboard.py --log build/sample.log
```

Trong trình duyệt của Ubuntu mở địa chỉ loopback cổng 8765. Trang ghi FILE REPLAY để tránh nhầm với log kit. Dashboard Python tối thiểu hiển thị dòng hợp lệ/lỗi checksum. Không có chuyện tự thêm firewall hoặc giả vờ BLOCK trên kit.

Khi người 1 có log thật, xác định thiết bị USB-UART trên Ubuntu rồi:

```bash
.venv/bin/python tools/dashboard.py --serial /dev/ttyUSB0 --baud 115200
```

Tên ttyUSB0 chỉ là ví dụ, có thể là ttyACM0. Trong VirtualBox cần chuyển đúng USB device sang Ubuntu; lỗi quyền cổng cần cấp nhóm dialout cho user rồi đăng nhập lại. Chỉ một chương trình mở UART tại một thời điểm. Không chạy bootloader song song với đọc log. $IDS đang giữ fields thô, chưa đoán ý nghĩa từng cột của firmware mới.

## Những gì cần bàn giao

rtl/ai_core.v + model ROM/quant_params + spec + vectors + metrics + README. Có thể hoàn thành chúng độc lập; ghép PCAP đặc trưng RTL, Ethernet hai chiều, chính sách chọn IP và MQTT duy trì khi chặn phải chờ nhóm.

Xem reports/VERIFICATION.md để phân biệt phần đã kiểm chứng trong cloud và phần cần chạy trên Ubuntu 26.04 của bạn.

### Dashboard hai phần với log cảm biến đã thu

Có thể đưa thêm file sensor và receiver của một phiên vào dashboard:

```bash
.venv/bin/python tools/dashboard.py --log build/sample.log \
 --sensor-log data/captures/normal_train01/sensor.jsonl \
 --received-log data/captures/normal_train01/received.jsonl
```

Bên trái hiển thị số lần gửi, lỗi, nhiệt độ và đồ thị; bên phải hiển thị log FPGA. Nếu bên phải là sample.log thì vẫn ghi FILE REPLAY, không coi là log kit. Số giây từ bản tin cuối của một phiên cũ tăng lên là bình thường; không phải bằng chứng broker đang ngừng hoạt động. Muốn giám sát lúc capture đang chạy, mở dashboard trong Terminal thứ hai và trỏ đúng file hiện tại.

### Thay đổi điều kiện để thu thêm phiên

Cú pháp run_capture.sh: MODE SPLIT ID SECONDS [PPS] [SENSOR_INTERVAL]. PPS là tốc độ mục tiêu của nguồn thử (1..500), khoảng cảm biến 0.2..5 giây. Tốc độ thực tế phải đọc PCAP/source.log, không mặc định bằng tham số. Seed thay đổi theo RUN_ID và được lưu trong scenario.txt. Ví dụ thu bình thường tải cao hơn:

```bash
sudo bash lab/run_capture.sh normal train normal_train02 30 200 0.2
```

Không chỉ thu đúng một cấu hình rồi kết luận mô hình tổng quát. Khi tăng số nguồn hoặc thay loại dịch vụ, cần thu và đánh giá thêm dữ liệu.

## Sửa lỗi Ubuntu: Mosquitto không mở được cấu hình trong /tmp hoặc Home

Bài test MQTT bản mới chạy `mosquitto -p PORT` ở chế độ chỉ loopback, không đọc cấu hình tạm. Không cần tắt AppArmor hoặc chạy cả bài test bằng sudo. Nếu lỗi vẫn xảy ra, đọc log cụ thể để chẩn đoán thay vì coi AppArmor là nguyên nhân chắc chắn.

Script lab bản mới tạo cấu hình tạm dưới /etc/mosquitto/part2-lab (ngoài conf.d), dùng riêng cho broker trong namespace và xóa file sau phiên. Một bản sao được lưu trong thư mục phiên để đối chiếu. Không sửa cấu hình dịch vụ Mosquitto mặc định. Thư mục part2-lab có thể còn rỗng sau khi chạy.

### Khi log kernel xác nhận AppArmor DENIED cho profile mosquitto

Nếu `/usr/sbin/mosquitto` bị profile `mosquitto` chặn đọc `/etc/mosquitto/part2-lab/session.*.conf`, dùng helper hẹp thay vì tắt AppArmor hoặc đổi đường dẫn cấu hình tiếp:

```bash
python3 scripts/allow_lab_apparmor.py
sudo python3 scripts/allow_lab_apparmor.py --apply
```

Lệnh đầu chỉ hiển thị kế hoạch. Lệnh thứ hai tự tìm một trong hai tên profile phân phối thường dùng, tìm local include của chính profile đó, giữ nguyên quy tắc hiện có và thêm DUY NHẤT quyền đọc các file cấu hình phiên lab. Nó không cấp quyền ghi, không sửa profile chính, không mở quyền đọc /tmp/Home, không tắt AppArmor. Nếu không tìm thấy profile/local include rõ ràng, nó dừng. Nó sao lưu local include nếu đã tồn tại, kiểm tra cú pháp không nạp kernel, sau đó reload chỉ Mosquitto. Nếu lỗi nó khôi phục file; thông báo riêng nếu không xác nhận được việc reload lại policy cũ.

Sau khi báo OK, giữ nguyên các namespace đã tạo và dùng tên phiên mới:

```bash
sudo bash lab/run_capture.sh normal train normal_train02 20
```

Giữ thư mục phiên lỗi cũ để chẩn đoán. Các dòng DENIED của Firefox không liên quan tới broker MQTT. Trên Ubuntu có chính sách tùy chỉnh khác, không tự đoán đường dẫn hoặc thêm quyền rộng hơn; gửi thông báo của helper để kiểm tra tiếp.

### Bổ sung đối chứng bình thường hai nguồn trước khi train

Không để tập normal chỉ có một IP nguồn còn mọi tập tấn công có hai IP, vì f3 (src_count) có thể trở thành dấu hiệu giả. sensor_client.py bản mới có --client-prefix; run_capture.sh nhận tham số thứ bảy NORMAL_CLIENTS (1 hoặc 2, mặc định 1, chỉ áp dụng cho normal). Với 2, namespace p2source cũng chạy một cảm biến MQTT HỢP LỆ, client ID riêng tránh làm ngắt kết nối cảm biến chính. Hai log được ghi riêng; capture chỉ được đăng ký khi cả hai có ít nhất một lần publish thành công.

```bash
sudo bash lab/run_capture.sh normal train normal_train03 20 200 0.2 2
sudo bash lab/run_capture.sh syn train syn_train02 20 80
sudo bash lab/run_capture.sh scan train scan_train02 20 200
```

Số 200 ở vị trí PPS của normal không tạo lưu lượng tấn công; khoảng gửi cảm biến là 0.2 giây, số nguồn là 2. Hai phiên tấn công bổ sung thay đổi tốc độ để mô hình không chỉ học tốc độ cố định của một kịch bản. Các phiên cũ vẫn được giữ và có thể dùng; đây là bổ sung đối chứng, không phải đổi nhãn chúng.

Sau khi đã kiểm tra đối chứng hoạt động, thu cả normal một nguồn và normal hai nguồn trong validation/test, cùng các phiên SYN/scan có tốc độ khác nhau. Ví dụ hai nguồn:

```bash
sudo bash lab/run_capture.sh normal val normal_val01 20 200 0.5 2
sudo bash lab/run_capture.sh syn val syn_val01 20 250
sudo bash lab/run_capture.sh scan val scan_val01 20 60
sudo bash lab/run_capture.sh normal test normal_test01 20 200 0.3 2
sudo bash lab/run_capture.sh syn test syn_test01 20 120
sudo bash lab/run_capture.sh scan test scan_test01 20 150
```

Chỉ dùng tên ID chưa tồn tại. Xem capture.log và PCAP của từng phiên; source_count có thể khác ở từng cửa sổ, cần thống kê sau khi tạo feature để kiểm tra đối chứng. Nhiều nguồn hợp lệ hơn, dịch vụ khác và thay đổi mạng vẫn là những điều kiện cần đánh giá thêm; đối chứng hai nguồn không tự chứng minh khả năng tổng quát.

### PCAP có timestamp không tăng theo thứ tự ghi

Linux có thể ghi các gói vào PCAP với timestamp hơi lệch thứ tự. Bộ trích xuất mới không yêu cầu sắp xếp toàn bộ file: mỗi gói được cộng vào cửa sổ của chính timestamp đó, nên không bỏ gói và không thay timestamp. File PCAP gốc không bị sửa. Công cụ ghi timestamp_reversals và max_backward_seconds trong stats của từng capture ở file .meta.json, đồng thời phát RuntimeWarning một lần mỗi file có lệch. Cảnh báo không làm lệnh thất bại. Nếu mức lệch lớn bất thường, cần xem lại clock/PCAP trước khi dùng dữ liệu; việc chạy xong không tự xác nhận chất lượng timestamp.

Sau khi thay part2/features.py bằng bản mới, chạy lại bước tạo feature. Nếu output cũ đã tồn tại, dùng tên mới thay vì ghi đè. Không cần thu lại PCAP chỉ vì thông báo Unsorted capture timestamps của bản cũ.

## Project Gowin theo mô hình lab v1 đã bàn giao

Thư mục gowin/lab_model_v1 chứa project dùng trọng số thực tế người dùng đã gửi, không phải model demo nhân tạo. Xem README_GOWIN_VI.md trong đó. Chỉ chạy Synthesis, không Run All/PNR hoặc nạp riêng xuống kit. ROM được nhúng vào RTL nên không cần sửa đường dẫn HEX.

Muốn xuất project cho model khác đã train và có đủ HEX/vectors:

```bash
.venv/bin/python tools/prepare_gowin.py --model build/lab_model_v1 --output build/gowin_export_v1
```

Đầu ra phải chưa tồn tại. Generator kiểm tra HEX/model/vectors khớp nhau; nó không chạy Gowin và không khẳng định timing. Hướng dẫn bổ sung trong gói Gowin lab_model_v1 là hướng dẫn cho bản v1 đã review, không tự coi model tương lai có cùng scale/divisor.
