# Bàn giao lõi AI v1 cho người 1 và 3

## Trạng thái có bằng chứng

- Model 6-8-3 float/integer được báo cáo đúng 96/96 cửa sổ test từ 6 capture. Luật ngưỡng cũng đúng 96/96; chưa chứng minh AI tốt hơn.
- Icarus: 360 vector khớp integer Python, 84 chu kỳ từ nhận start đến done.
- Gowin Synthesis do người dùng cung cấp: 447 logic (395 LUT + 52 ALU), 246 FF, latch 0, BSRAM 0, DSP 1. Clock trong báo cáo 50MHz, Fmax ước tính 56.3MHz; chưa có timing sau routing/đo kit. Project SDC ban đầu mục tiêu 27MHz, cần thống nhất khi ghép.
- Lab MQTT đã tạo/thu SYN và scan nhưng các phiên được cung cấp vẫn gửi thành công 20/20: chưa chứng minh dịch vụ gián đoạn rồi được khôi phục nhờ bộ lọc.

## File dùng khi ghép

1. gowin/lab_model_v1/src/ai_core_model_v1.v — module ai_core với ROM v1 nhúng. Chỉ thêm một định nghĩa ai_core, bỏ stub khỏi danh sách source của top khi tích hợp.
2. gowin/lab_model_v1/firmware/ai_quant_v1.h — helper C tính raw->q->feat, không điều khiển phần cứng.
3. spec/FEATURES_V0.md và spec/AI_INTERFACE.md — công thức, đóng gói và handshake.
4. handoff/INTEGRATION_VECTORS.json — ví dụ raw->packed->scores->class tính từ v1; không phải ground-truth dữ liệu mạng.
5. verification/vectors.txt + tb_ai_core.v trong project Gowin — kiểm thử lõi số học độc lập.

Model JSON SHA256: b67f6de6b847a4d2500e2af130c9e31091c92a9cbd3f68de84fe0a31d2a59007. Divisors [8,1,1,1,1,4], shift1=6, shift2=2. Không đổi scale mà giữ trọng số cũ.

## Người 3 cần khớp

Chiều ngoài->trong; IPv4 hợp lệ; cửa sổ 1 giây. f0 số gói, f1 floor(tổng IPv4 Total Length/số gói), f2 floor(127*SYN_open/số gói), f3 IP nguồn phân biệt, f4 IP đích phân biệt, f5 cổng TCP/UDP đích phân biệt. SYN_open là SYN=1 ACK=0. Empty window sáu số 0.

Hiện model dùng distinct=exact. Nếu phần cứng dùng bitmap, phải cho Python tính cùng hash/kích thước và đánh giá lại; không coi số bit bật luôn bằng số giá trị khác nhau. Mốc cửa sổ/reset phải căn với PCAP khi đối chiếu. Frame CRC sai, phân mảnh/không hỗ trợ, overflow cần chính sách và counters rõ; không đưa số liệu lỗi vào model mà không ghi nhận.

## Người 1 cần khớp

Hàm ai_v1_pack trong header nhận packet_count, ip_byte_sum, syn_open_count, src_count, dst_count, dst_port_count. Trả 48 bit trong uint64, q0 ở byte thấp. Ghi 32 bit thấp vào FEAT_LO, 16 bit tiếp vào FEAT_HI rồi START. Input 0..127. start và done xung 1 clock, start khi busy bỏ qua. Score0/1/2 int16 có dấu, lớp 0 bình thường, 1 SYN flood, 2 vertical scan, hòa điểm chọn lớp nhỏ hơn. Giữ nguyên địa chỉ thanh ghi AI theo wb_ai_regs.

Ví dụ logic, dùng macro thật của firmware nhóm:

```c
uint64_t f = ai_v1_pack(pkt, bytes, syn, src, dst, ports);
AI_FEAT_LO = (uint32_t)f;
AI_FEAT_HI = (uint32_t)(f >> 32);
AI_CTRL = AI_CTRL_START;
/* Chờ DONE với timeout, đọc RESULT và SCORE theo driver thực tế. */
```

Helper có chia uint64; kiểm tra build RISC-V liên kết libgcc như build_fw.sh. Hành vi ABORT hiện không trực tiếp reset ai_core; timeout không tự có nghĩa lõi đã hủy, phải kiểm tra busy/reset khi phục hồi.

## Không thuộc trách nhiệm riêng ai_core

AI không giữ địa chỉ IP, không trực tiếp DROP Ethernet. Chọn IP nghi vấn, whitelist/blacklist, xác nhận 2 cửa sổ và TTL thuộc đặc trưng/chính sách CPU/bộ lọc. Dashboard chỉ đọc log, không tự ghi luật. Số chu kỳ AI không bao gồm thời gian cửa sổ/xác nhận.

## Bài kiểm tra ghép theo thứ tự

A. Cấp vector feat đã có, gọi từ CPU, đối chiếu scores và class với Python.
B. Một PCAP/header stream có mốc cửa sổ xác định: so raw counters -> feat hex giữa Python và phần cứng.
C. Bridge cho qua hai chiều + ARP, luật chặn cố định, đếm CRC/overflow trước khi dùng AI.
D. AI ra luật: nguồn thử nghiệm bị chặn, nguồn hợp lệ đi qua; đo lượng lọt qua trước khi chặn và lỗi chặn nhầm.
E. Chốt clock/constraints toàn hệ thống và timing sau routing, nạp kit rồi đo tác dụng MQTT.
