# V6.1 — sửa đường timing RX cổng B, giữ model AI V6

Báo cáo Gowin bạn gửi đã hoàn tất tổng hợp, Place & Route và sinh bitstream. Thiết kế dùng63%logic,48%register,15BSRAM và1DSP, không có latch. Tuy nhiên cổngB chỉ đạt Fmax48,696MHz khi yêu cầu50MHz:8điểm setup vi phạm, slack xấu nhất−0,268ns. Clock hệ thống27MHz và cổngA50MHz đạt các đường nội bộ được báo cáo. Đây là kết quả **V6 trước sửa**, chưa phải kết quả V6.1.

## Bản sửa này làm gì

`rtl/part4_eth/rmii_rx.v` thêm3FF trong nhánh lấy mẫu cạnh xuống: chốt dữ liệu/carrier tại cạnh xuống, đồng bộ cùng nhau sang thanh ghi cạnh lên, rồi CRC/FSM xử lý ở cạnh lên kế tiếp. Logic CRC có chu kỳ20ns thay vì bị đặt trong nửa chu kỳ10ns. Nhánh SAMPLE_NEG=0 giữ nguyên. Nhánh SAMPLE_NEG=1 thêm1chu kỳ REF_CLK (20ns tại50MHz).

Model V6, RTL AI, firmware, dữ liệu train, địa chỉ bảo vệ/whitelist, policy, chân CST và SDC giữ nguyên từng byte. Không train lại, không hạ clock RMII, không đặt false-path/multicycle để bỏ qua lỗi. Pin63 và cảnh báo generic clock PR1014 vẫn cần được xem lại sau P&R và đối chiếu phần cứng.

## Chạy trên Windows

Giải nén `ghep_phan1_ai_v6_1.zip` vào một thư mục mới. Mở CMD và chạy file bằng đường dẫn thực tế: giữ Shift, nhấn chuột phải `CHUAN_BI_GOWIN.py`, Copy as path; gõ `python ` rồi dán đường dẫn và Enter. Nếu dùng launcher `py`, thay `python` bằng `py`.

```text
python CHUAN_BI_GOWIN.py
```

Mở **gateway_phan1_v6_1.gprj** vừa tạo, top **gowin_top**, device **GW1NR-LV9QN88PC6/I5**. Chạy Synthesize rồi Place & Route. Sau đó chạy, tại thư mục gói hoặc bằng đường dẫn đầy đủ tới file:

```text
python THU_BAO_CAO_GOWIN.py
```

Gửi **BAO_CAO_GOWIN_V6_1.zip** để kiểm lại. Collector mới gom cả source RX/AI/wrapper để đối chiếu đúng bản sửa. Nếu báo fileZIP đã tồn tại, đổi tên bản báo cáo cũ. Dùng thư mục V6.1 mới giúp giữ riêng kết quả V6 trước sửa.

V6.1 chỉ được xác nhận đóng timing sau khi báo cáo mới có0vi phạm setup/hold tại27/50/50MHz. Việc sinh được `.fs` chưa xác nhận timing hay hoạt động trên bo. Môi trường chuẩn bị gói không có Gowin; không có số Fmax V6.1 để công bố lúc này.

## Kiểm tra trên Ubuntu

```bash
python3 ~/Downloads/ghep_phan1_ai_v6_1/KIEM_TRA_GHEP_V6_1.py
python3 ~/Downloads/ghep_phan1_ai_v6_1/KIEM_TRA_GHEP_V6_1.py --full
```

Lệnh đầu kiểm hash,3.762vector bus,CPU POST37/37,5cửa sổ feature, RX hai cạnh và MAC hai chiều. `--full` thêm demo40giây và hệ thống RMII/CPU/AI. Cần Python3+Icarus; không cần train hoặc cài thư viện AI. Log mới nằm trong `sim/out/`; bằng chứng chuẩn bị gói nằm trong `verification/recorded/`.

Bài RX so với source V6 trước sửa:40khung cho mỗi chế độ cạnh,24.273byte mỗi chế độ,30CRC tốt và10CRC lỗi; nội dung/SOF/EOF/CRC giữ nguyên, nhánh cạnh xuống trễ đúng1chu kỳ. Có kiểm reset và các pha đầu vào khác nhau, IFG tối thiểu. Bài MAC kiểm payload+FCS cổngB, CRC hỏng bị bỏ và khung dài1.518byte cả hai chiều. Đây là kiểm chức năng, không thay thế STA sau P&R.

## File và giới hạn bàn giao

- `GOWIN_V6_REVIEW.json`: kết quả đọc báo cáo V6 bạn gửi; SHA của archive đầu vào được lưu, không cần sửa nhãn/train.
- `PATCH_V6_1.json`: phạm vi sửa và hash model/firmware/RX.
- `READY_REPORT.json`, `MO_KET_QUA_GHEP_V6_1.html`: kết quả và phạm vi xác nhận hiện tại.
- `rtl/part2_ai/`, `fw/part2/`, `training/`: model/header/cache/PCAP/CSV V6 giữ nguyên; xem README trong training khi muốn tái tạo.
- `reference/v6_before_timing_fix/`: source RX và bằng chứng mô phỏng của V6 cũ, chỉ để đối chiếu.

Gói gốc vẫn có12lỗi Normal trên tập học,1SYN miss ở development cùng nguồn; lab lịch sử218/219 với1Normal nhậnScan. Không có test độc lập mới, model không đổi nên các số này không đổi. Prototype MAC vẫn có overflow ở burst, P3 vẫn là tham chiếu. Trước chạy mạng thật, nhóm cần rà soát clock/CDC, reset từng miền, timing I/O theo PHY/dây, pin/điện áp; cấu hình đích bảo vệ mặc định192.168.10.2/32 và whitelist.2/.20 phải khớp lab. Sau khi sửa C config cần build firmware và chạy kiểm lại. Chưa có xác nhận bo thật hoặc chặn tự động an toàn.

Model SHA256: `3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515`.
