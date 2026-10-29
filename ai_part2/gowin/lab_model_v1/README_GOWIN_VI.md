# Tổng hợp riêng AI v1 bằng Gowin — chưa nạp kit

## Gói này dùng mô hình nào?

CHÍNH trọng số lab_model_v1 người dùng gửi: MLP 6-8-3, divisors [8,1,1,1,1,4], shift1=6, shift2=2, hidden_scale=32, score_scale=128. Trọng số/bias nhúng thành ROM tổ hợp (function/case) trong src/ai_core_model_v1.v; không cần file HEX hoặc include. Một phép nhân dữ liệu dùng chung theo FSM; biểu thức địa chỉ ROM còn có nhân hằng số, tool quyết định DSP/LUT thực tế.

Giữ nguyên module và cổng ai_core. Không đưa ai_core cũ/stub và file này vào cùng project. Không dùng RTL này cho model khác.

## Mục tiêu hiện tại

Chỉ chạy Synthesis để khảo sát khối AI độc lập. Không xác nhận PHY, firewall, firmware hoặc timing sau routing.

Tổng các cổng song song của ai_core vượt số chân I/O khả dụng nếu đưa hết ra kit. Khi ghép chúng là tín hiệu nội bộ. Vì vậy KHÔNG chạy Run All/Place & Route, KHÔNG nạp bitstream của project này. Không cần cắm Tang Nano.

## Các bước trên Windows

1. Tải gowin_ai_v1.zip từ GitHub, Extract All vào đường dẫn ngắn không dấu, ví dụ C:\DoanHTS\gowin_ai_v1\.
2. Trong thư mục phải có ai_core_v1.gprj, src, constraints, verification, firmware, reference. Không mở project bên trong ZIP.
3. Mở Gowin EDA -> File -> Open Project (hoặc Open), chọn ai_core_v1.gprj.
4. Kiểm tra device GW1NR-9C, part GW1NR-LV9QN88PC6/I5. Đây là part từ template Tang Nano 9K chính thức của Sipeed; đối chiếu chip trên kit của nhóm khi tạo thiết kế nạp.
5. Source chỉ có src/ai_core_model_v1.v và constraints/ai_core.sdc. KHÔNG thêm testbench hoặc stub. Top module ai_core (project chỉ có một module nên có thể tự nhận).
6. Ở Process/Flow chọn Synthesize hoặc Synthesis, chạy RIÊNG bước đó. Tên menu khác nhẹ theo phiên bản EDA.
7. Chờ hoàn thành, mở Synthesis Report. Gửi bảng tài nguyên LUT/FF/BSRAM/DSP nếu tool có và các cảnh báo liên quan. Nếu lỗi, gửi ERROR đầu tiên và các dòng xung quanh, không chỉ dòng failed.

Constraints đặt MỤC TIÊU 27MHz, chưa chứng minh đạt timing sau routing. Clock 100MHz trong testbench Icarus chỉ dùng mô phỏng logic, không phải tần số chip đã đạt.

## Nếu project không mở được

GPRJ dựa theo template chính thức Sipeed (URL trong EXPORT_MANIFEST.json). Nếu phiên bản EDA không đọc được, New Project Wizard -> chọn device/part trên -> thêm đúng hai file -> top ai_core -> chỉ Synthesis.

Tùy chọn dòng lệnh (thay vị trí cài Gowin thực tế):

```text
"C:\DUONG_DAN_GOWIN\IDE\bin\gw_sh.exe" "C:\DoanHTS\gowin_ai_v1\synth_ai.tcl"
```

Tcl gọi run syn, không chạy PNR. Cloud không có Gowin, nên chưa xác nhận câu lệnh với từng phiên bản EDA; nếu không nhận lệnh, dùng GUI và gửi phiên bản/lỗi.

## Phần đã kiểm chứng trong cloud

- HEX khớp JSON; 360 vector khớp tính toán Python số nguyên.
- RTL gốc được biên dịch lại từ source và RTL nhúng ROM đều PASS 360 vector, 84 chu kỳ; không chạy sim.vvp người dùng tải lên.
- Yosys 0.52 phân tích/elaborate RTL và CHECK báo 0 problems. Đây không phải mapping/timing Gowin.
- Hàm lượng tử hóa C khớp Python 204 trường hợp zero/biên/ngẫu nhiên.
- XML đọc được, source tồn tại; Tcl kiểm tra cú pháp/đường dẫn qua stub, không phải chạy tool Gowin.

## Giao cho người 1 và 3

firmware/ai_quant_v1.h cung cấp:

```c
uint64_t feat = ai_v1_pack(pkt_count, ip_byte_sum, syn_open_count,
                         src_count, dst_count, dst_port_count);
```

Đầu vào là thống kê RAW cùng cửa sổ. ip_byte_sum cộng IPv4 Total Length, không dùng độ dài khung Ethernet. SYN chỉ tính SYN=1, ACK=0. q0 ở bit 7:0 tới q5 ở bit 47:40; CPU ghi 32 bit thấp vào FEAT_LO, 16 bit tiếp vào FEAT_HI.

q0=clip(pkt_count>>3); q1=clip(mean_ip_len); q2=clip(floor(127*syn_open_count/pkt_count)); q3=clip(src_count); q4=clip(dst_count); q5=clip(dst_port_count>>2). clip 0..127, cửa sổ rỗng trả 0. Helper có phép chia uint64; firmware RISC-V freestanding phải liên kết libgcc như build_fw.sh hiện có.

Mô hình train distinct=exact. Nếu RTL dùng bitmap, cần mô phỏng đúng hash/kích thước, đối chiếu PCAP và đánh giá/train lại nếu cần. Không tự đổi divisor/shift mà giữ trọng số cũ.

## Đọc đúng kết quả

Float, integer và luật ngưỡng đều được báo cáo đúng 96/96 cửa sổ test. Chưa chứng minh AI hơn luật. Test gồm 6 capture; toàn bộ 18 capture/288 cửa sổ. Các cửa sổ trong một capture có tương quan, không coi là 96 thí nghiệm độc lập.

84 chu kỳ ở clock THỰC SỰ đạt 27MHz tương đương khoảng 3.11us. Phản ứng firewall còn gồm cửa sổ thống kê, xác nhận và firmware. Chưa có kết quả timing Gowin hoặc lọc Ethernet thật trong gói này.
