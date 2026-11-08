# Phần 2 — AI V6 riêng để bàn giao

Đây là phần AI của bạn, giữ nguyên model V6 đã kiểm tra. Gói chỉ chứa core AI, trọng số, hàm C lượng tử hóa, chuẩn giao tiếp và bộ kiểm thử. CPU PicoRV32, bus Wishbone, firmware hệ thống, MAC/PHY, RTL trích đếm/lọc và top/demo của các phần khác không nằm trong gói này.

**Gửi nguyên `phan2_ai_v6_ban_giao.zip` cho người tích hợp. Không cần train lại.**

| File | Công dụng |
|---|---|
| `rtl/ai_core_model_v6.v` | Core 6–8–3, module `ai_core`, đã nhúng trọng số |
| `firmware/ai_quant_v6.h` | Chuyển sáu counter thành 48 bit đúng model |
| `firmware/ai_v6_integration.h` | Bỏ suy luận khi N = 0; N từ 1 đến 7 vẫn hợp lệ |
| `firmware/example_prepare.c` | Ví dụ tạo low32/high16, không phụ thuộc CPU/bus |
| `model/model.json` | Bộ trọng số số nguyên đã chốt |
| `model/` | Model float, tệp hex, metrics và nguồn gốc dữ liệu để đối chiếu |
| `HOP_DONG_GHEP_AI_V6.md`, `spec/FEATURES_V0.md` | Port, handshake, packing và chuẩn đặc trưng |
| `verification/` | 3.762 vector q, 41 tham chiếu counter, testbench core và bài kiểm C |
| `gowin/ai_core_v6.gprj` | Synthesize riêng core; không phải project nạp bo |

## Kiểm tra nhanh

Mở terminal tại thư mục vừa giải nén, chạy:

```bash
python3 KIEM_TRA_PHAN2.py
```

Trên Windows dùng `python` hoặc `py` thay `python3`. Lệnh kiểm hash và tính toán số nguyên trên toàn bộ tham chiếu; không cần thư viện AI.

Nếu đã cài GCC và Icarus Verilog, kiểm thêm C và RTL:

```bash
python3 KIEM_TRA_PHAN2.py --c --rtl
```

Kết quả mong đợi: Python kiểm 3.762 vector và 41 counter; C kiểm 41 case (40 hợp lệ, một rỗng); RTL kiểm 3.762 vector, mỗi lần suy luận mất 84 chu kỳ. Testbench còn thử reset giữa phép tính, START khi busy, thay feat sau khi đã chốt và độ dài xung DONE.

Log mới nằm tại `verification/build/`. Kết quả đã ghi khi đóng gói nằm tại `verification/recorded/`. Thiếu compiler C hoặc Icarus sẽ báo lỗi rõ khi chọn tùy chọn tương ứng.

## Người nhận ghép như sau

1. Thêm `rtl/ai_core_model_v6.v` vào project của họ, chỉ giữ một định nghĩa module `ai_core`.
2. Cung cấp sáu counter đúng receiver /32 và cửa sổ một giây: số gói, tổng byte IPv4, số SYN không ACK, số IP nguồn, số IP đích và số cổng đích phân biệt. Hàm C nhận tổng byte và số SYN thực, không nhận mean/percent đã làm tròn.
3. Dùng đúng divisors `[8,2,1,1,1,1]`. Core nhận 48 bit q; trả class 0/1/2 và ba score int16 có dấu. Cửa sổ N = 0 phải bỏ START.
4. Nối handshake theo `HOP_DONG_GHEP_AI_V6.md`, chạy lại các tham chiếu, sau đó kiểm CPU/bus/trích đếm/policy và P&R trong project của người nhận.

Model SHA256: `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`.

Đọc `GIOI_HAN_MODEL.md` để biết các lỗi và giới hạn dữ liệu đã ghi nhận. Lần tách gói này không tạo kiểm thử lưu lượng độc lập mới hoặc xác nhận chạy trên bo.

Nếu cần mã train, cache, PCAP và CSV, dùng gói riêng `phan2_ai_v6_train_va_du_lieu.zip`. Gói đó không bắt buộc để ghép core.
