# Schema log cho dashboard — cần người 1 xác nhận trước khi dùng với kit

Các dòng ASCII kết thúc CRLF. Dạng $PAYLOAD*CS; CS là XOR mọi byte ASCII giữa $ và *, 2 chữ số hex.

- MODE,DETECT hoặc MODE,BLOCK.
- CNT,fwd,drop_bl,drop_syn,crc_err,overflow: unsigned 32-bit; đây là giá trị bộ đếm, không tự suy là gói/giây.
- BLK,ipv4,DOS|SCAN,ttl_seconds; UNB,ipv4. Dashboard chỉ ghi nhận log, không thực thi firewall.
- IDS theo lựa chọn --ids-schema pdf-v1: đúng 11 trường sau IDS:
  window_id,raw_class,filtered_class,packet_count,mean_ip_bytes,syn_value_reported,src_count,dst_count,dst_port_count,flags,ai_cycles.

0 bình thường, 1 SYN flood, 2 vertical scan. Đơn vị syn_value_reported cần firmware chốt; dashboard không dùng nó để lượng tử hóa. Schema IDS lấy từ cấu trúc ví dụ PDF, là hợp đồng đề xuất, chưa có log kit thật để xác nhận. Mặc định --ids-schema opaque chỉ hiển thị dòng IDS nguyên văn, không đoán cột.

FILE_REPLAY/FILE_FOLLOW luôn được đánh dấu khác SERIAL. Mở serial chỉ chứng minh chương trình đang đọc một cổng, không tự chứng minh dữ liệu Ethernet đã bị DROP. Hết TTL chưa có UNB được hiển thị “chờ xác nhận”, không tự coi đã gỡ.
