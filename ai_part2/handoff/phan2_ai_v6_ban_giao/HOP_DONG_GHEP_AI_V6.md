# Hợp đồng ghép phần AI V6

Thêm `rtl/ai_core_model_v6.v` vào source của hệ thống người nhận, dùng module tên `ai_core`. Trọng số đã nhúng trong ROM dạng case; core không đọc tệp hex lúc chạy. Chỉ giữ một định nghĩa module `ai_core` trong source đang dùng.

| Port | Hướng | Quy ước |
|---|---|---|
| `clk` | in | Clock chung; template dùng 27 MHz |
| `rst_n` | in | Reset mức 0, **đồng bộ cạnh lên clk**, giữ qua ít nhất một cạnh lên |
| `start` | in | Xung một chu kỳ khi busy = 0; core chốt feat tại cạnh nhận START |
| `feat[47:0]` | in | Sáu q, mỗi byte từ 0 đến 127; q0 ở byte thấp nhất |
| `busy` | out | 1 khi đang tính; START trong busy bị bỏ qua |
| `done` | out | Xung một chu kỳ khi kết quả mới hợp lệ |
| `class_id[1:0]` | out | 0: Normal, 1: SYN flood, 2: Vertical scan |
| `scores[47:0]` | out | Ba score int16 có dấu: score0 ở bit 15:0, score2 ở bit 47:32 |

Core cần **84 chu kỳ** từ START được nhận tới DONE theo testbench đi kèm. Thời gian này chưa bao gồm đọc gói, trích đặc trưng, bus hoặc chặn. Sau DONE, kết quả giữ ổn định tới giao dịch tiếp theo/reset. Dùng DONE để nhận kết quả mới. Khi so score, tách từng lane và diễn giải thành signed int16. Score không phải xác suất; argmax hòa chọn lớp có chỉ số nhỏ nhất.

Kiến trúc 6–8–3, weight int8 có dấu, bias/accumulator int32, shift1 = 5, ReLU hidden từ 0 đến 127, shift2 = 0 và score bão hòa int16. Không đổi trọng số, shift hoặc divisor riêng rẽ.

## Phía phần mềm người nhận

Include `firmware/ai_v6_integration.h` và gọi:

```c
ai_v6_prepare_window(N, total_ip_bytes, syn_open,
                     src_count, dst_count, port_count, &feat);
```

- Trả 0: cửa sổ rỗng, bỏ START và bỏ quyết định từ cửa sổ đó.
- Trả 1: chuyển low32/high16 của feat vào adapter rồi phát START. N từ 1 đến 7 vẫn hợp lệ dù q0 = 0.

`firmware/example_prepare.c` minh họa chuẩn bị hai word; `integration/instance_example.vh` minh họa nối core. Người nhận cung cấp map thanh ghi, adapter bus, reset/đồng bộ, latch DONE, timeout và sign extension phù hợp hệ thống của họ.

Bộ 41 tham chiếu counter gồm 40 lần suy luận và một cửa sổ rỗng. Bộ này kiểm phần nối mới; không tự thay bộ POST 37 case trong firmware của bản ghép trước.

## Phạm vi quyết định

Core trả class và score. Người tích hợp gắn kết quả với nguồn lưu lượng thực và policy chặn đã thống nhất. Nhiều cổng tổng hợp ở một receiver không tự chứng minh một IP nguồn đã vertical scan. Các giới hạn model/dữ liệu nằm trong `GIOI_HAN_MODEL.md`.

## Gowin

`gowin/ai_core_v6.gprj` chỉ để **Synthesize riêng core**, chọn top `ai_core` trong Configuration nếu IDE chưa tự chọn. Có thể dùng `gowin/synth_ai.tcl` để thiết lập top một cách tường minh.

Interface song song có 103 I/O khi làm top; các tín hiệu này phải nằm bên trong top hệ thống khi ghép. Không dùng project core này để Place & Route hoặc nạp trực tiếp kit. Người nhận ghép vào top của họ, áp chân/clock/CDC/timing và chạy lại P&R cùng bài kiểm toàn hệ thống. Gói không chứa CST hoặc bitstream bo. Báo cáo P&R của bản ghép trước không phải báo cáo standalone mới cho gói này.
