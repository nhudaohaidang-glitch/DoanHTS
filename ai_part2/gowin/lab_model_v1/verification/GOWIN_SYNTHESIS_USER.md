# Kết quả Gowin Synthesis do người dùng cung cấp

Nguồn: ảnh chụp báo cáo ai_core_v1_syn.rpt.html và Console kết thúc “GowinSynthesis finish”. Chưa nhận file HTML/netlist để phân tích độc lập; đây là ghi nhận báo cáo người dùng, không phải lần chạy Gowin trong cloud.

## Resource Utilization Summary

| Mục | Sử dụng | Theo báo cáo |
|---|---:|---:|
| Logic tổng | 447 (395 LUTs + 52 ALUs) / 8640 | 6% |
| Register/FF | 246 / 6693 | 4% |
| Register as Latch | 0 | 0% |
| BSRAM | 0 / 26 | 0% |
| DSP | 1 MULTADDALU18X18 | Không thấy tổng số DSP trong ảnh |
| I/O Port | 103 (51 input, 52 output) | Cổng logic của top độc lập |

Bảng Resource Usage Summary chi tiết ghi LUT=394, INV=1; bảng tổng hợp Utilization ghi 395 LUTs + 52 ALUs. Giữ nguyên cả hai cách thống kê của tool, không cộng hai bảng lại. Khi viết tóm tắt dùng bảng Utilization và giữ HTML gốc làm bằng chứng.

## Timing trong báo cáo Synthesis

Clock clk, period 20ns, constraint 50MHz. Actual Fmax được tool báo 56.3MHz, logic level 13. Đây là ước tính của synthesis, không phải đo clock trên board hoặc timing sau routing.

Project xuất ban đầu có SDC mục tiêu 37.037ns (~27MHz), nhưng ảnh report synthesis đang dùng 20ns. Chưa có bằng chứng SDC đó đã được áp dụng cho phép phân tích synthesis; có thể công cụ dùng setting synthesis riêng. Không tự sửa RTL hoặc đổi shift/model để giải quyết khác biệt clock. Khi ghép top hệ thống, người phụ trách tích hợp cần chốt clock 27MHz và cấu hình synthesis/SDC/PNR nhất quán.

84 chu kỳ đã kiểm chứng bằng RTL simulation. Nếu clock thực tế đạt 27MHz thì thời gian riêng lõi khoảng 3.11us; nếu đạt 50MHz thì khoảng 1.68us. Chưa có phép đo phần cứng. Các số này không gồm cửa sổ thống kê và chính sách xác nhận hai cửa sổ.

## Trạng thái và bước tiếp theo

- Lõi AI v1 đã có báo cáo tổng hợp riêng từ Gowin, dùng một DSP và không sinh latch.
- ROM tổ hợp nên không dùng BSRAM; điều này phù hợp với cách xuất trọng số hiện tại.
- 103 cổng logic không phải yêu cầu 103 chân GPIO khi ghép core làm module nội bộ qua bus/regs. Không PNR/nạp riêng module này như top của kit.
- Timing cuối cùng, ngân sách toàn FPGA, giao diện feature thực tế, firmware và tác dụng chặn Ethernet/MQTT vẫn cần kiểm thử tích hợp.
- Model, trọng số, divisor và shift không thay đổi trong cập nhật ghi nhận báo cáo này.
- Cả AI và baseline vẫn được báo cáo đạt 96/96 test windows; chưa chứng minh AI hơn luật hoặc đạt 100% trên mạng khác.
