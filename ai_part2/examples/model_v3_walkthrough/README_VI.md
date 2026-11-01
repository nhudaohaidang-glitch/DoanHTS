# Ví dụ tính model AI v3

Đọc tài liệu handoff/GIAI_THICH_MODEL_AI_V3_VI.md trong repository.

sample_windows.csv trích 3 dòng train thật của ba lớp và 1 cửa sổ test v3test01 thật mà model nhận sai. packet_excerpt.csv trích 11 gói IPv4 ingress trong chính cửa sổ lỗi, không chứa payload. Những dòng này để học cách tính, không phải bộ dữ liệu mới dùng train hoặc công bố accuracy.

Từ thư mục ai_part2 chạy: python3 examples/model_v3_walkthrough/demo.py
Script chỉ dùng thư viện chuẩn Python, đọc model, không huấn luyện hoặc đổi trọng số. Nó in raw, q, tổng trước dịch, hidden, scores và class. Một probe SYN đơn lẻ bổ sung được ghi rõ là ví dụ dựng, không phải gói đã bắt.
