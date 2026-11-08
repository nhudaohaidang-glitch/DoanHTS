# Bắt đầu học phần AI V6

1. Mở `DE_CUONG_HOC_AI_V6.pdf` để đọc theo chương và mục lục.
2. Mở `DE_CUONG_HOC_AI_V6.html` bằng Chrome/Firefox/Edge để thay đầu vào và xem phép tính, rồi làm năm câu tự kiểm. HTML chạy ngoại tuyến.
3. Dùng bản `.docx` để ghi chú/chỉnh dàn ý học cá nhân.
4. Thực hành theo mười buổi trong mục 13 và làm mười bài tập ở mục 14 trước khi xem đáp án.

Gói học dùng đúng model AI V6 đã bàn giao. Ba cặp PCAP/CSV trong `vi_du/` là các profile dẫn xuất của cùng nguồn IoT-23/Chris Sanders đã dùng; không phải test độc lập mới. PCAP/CSV giữ nguyên nội dung profile, thông tin đối chiếu nằm trong `VI_DU_DA_DOI_CHIEU.json`.

Mở terminal trong thư mục gói, chạy bằng Python chuẩn (Windows dùng `python` hoặc `py`):

```bash
python3 HOC_AI.py kiem-tra
python3 HOC_AI.py vi-du syn
python3 HOC_AI.py raw 489 40 125 2 1 1
python3 HOC_AI.py counter 489 19728 483 2 1 1
python3 HOC_AI.py giai-nen-pcap
```

Lệnh cuối tạo PCAP không nén trong `vi_du/pcap_da_giai_nen/` để mở bằng Wireshark. Không phát traffic hoặc sửa model.

Đây là tài liệu học. Bộ AI để gửi người tích hợp vẫn là `phan2_ai_v6_ban_giao.zip`; mã train/dữ liệu đầy đủ nằm trong `phan2_ai_v6_train_va_du_lieu.zip`. Các gói đó giữ nguyên, không cần tải lại để đọc bản PDF này.
