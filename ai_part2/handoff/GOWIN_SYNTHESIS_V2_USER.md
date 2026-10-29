# AI v2 — kết quả synthesis người dùng gửi

Nguồn: ba ảnh Resource/Timing Gowin ngày 29/10/2026. Chưa có HTML/netlist, bitstream hoặc file model v2 tải lên để kiểm hash gắn với các ảnh. Các số dưới đây là user-reported, không phải chạy Gowin trong cloud.

| Mục | Báo cáo |
|---|---|
| Logic | 445 (393 LUT + 52 ALU) / 8640, tool hiển thị 6% |
| Register | 246 / 6693, tool hiển thị 4% |
| Latch | 0 |
| BSRAM | 0 / 26 |
| DSP | 1 MULTADDALU18X18 |
| Standalone I/O | 103, gồm 51 input và 52 output |
| Clock synthesis | 50 MHz / 20 ns |
| Estimated Fmax synthesis | 56,4 MHz |
| Logic levels | 13 |

Bảng chi tiết LUT ghi 392, INV ghi 1; bảng tổng Logic ghi 393 LUT. Giữ nguyên cách báo của tool, không cộng đúp INV. Core có vẻ phù hợp ngân sách riêng, nhưng chưa biết toàn hệ thống CPU/Ethernet/buffer có vừa hoặc đạt timing hay không.

Fmax là ước tính sau synthesis, chưa phải routed timing hoặc tần số thực đo. SDC project xuất mục tiêu 27 MHz trong khi ảnh synthesis phân tích 50 MHz; khi ghép cần chốt clock/constraints thực. 84 chu kỳ ở 27 MHz tương ứng khoảng 3,11 us nếu clock/timing thực đạt, ở 50 MHz khoảng 1,68 us nếu clock đó được cấp và đạt timing. Không dùng các số này làm độ trễ phát hiện/chặn toàn hệ thống.

Ảnh trước đó: validation float/integer đúng 160/160 (80 normal,48 SYN,32 scan), 424 vectors PASS và 84 chu kỳ, 0 convergence warnings. Holdout có 210/210 đúng trên 10 capture (105 normal,63 SYN,42 scan), FPR0, macro-F1=1, baseline cũng100%. Đây là kết quả người dùng cung cấp; chưa độc lập đọc dữ liệu/model v2. Hai tình huống retry và scan slow đúng trong holdout mới không chứng minh phân biệt mọi hành vi tương tự hoặc tổng quát sang IoT-23.

Giai đoạn tiếp theo: công cụ tools/make_handoff_v2.py kiểm tính nhất quán model/freeze/export/holdout và tạo gói dành cho người 1/3. Tiếp đó kiểm vector qua CPU, counters từ header, bridge/bộ lọc, timing sau route và đo việc chặn trên mạng thật. 103 I/O chỉ là giao diện core riêng, không yêu cầu dùng 103 chân bo khi tích hợp.
