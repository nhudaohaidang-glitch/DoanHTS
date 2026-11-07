# ai_core 6-8-3

Cổng giữ theo stub trong repo: clk, rst_n, start, feat[47:0], busy, done, class_id[1:0], scores[47:0]. Không lấy CRC Ethernet hoặc địa chỉ IP trong ai_core. CPU/chính sách lọc định danh nguồn riêng.

- Reset đồng bộ mức thấp, ưu tiên cao hơn start, bỏ giao dịch đang tính.
- start nhận tại cạnh lên khi busy=0; chốt toàn bộ feat tại đó. start lúc busy=1 bị bỏ qua.
- busy=1 trong lúc tính, về 0 khi done=1.
- done là xung 1 chu kỳ. scores/class_id chỉ cập nhật khi done, giữ tới kết quả kế tiếp/reset.
- class_id: 0 bình thường, 1 SYN flood, 2 vertical scan.
- scores[15:0]=lớp0, [31:16]=lớp1, [47:32]=lớp2. Score int16 có dấu, cùng scale. Không phải xác suất phần trăm.
- Argmax đồng điểm chọn lớp có số nhỏ hơn.

Trọng số w1/w2 signed int8, bias signed int32. Hidden ReLU bão hòa 0..127, output bão hòa -32768..32767. Weight/bias round-to-nearest-even khi xuất file; dịch phải số âm làm tròn về âm vô cùng (arithmetic shift), không làm tròn về 0. Python và RTL tuân theo cùng quy tắc. Kiểm tra cận int32 trước khi xuất model.

ROM lấy w1.hex,b1.hex,w2.hex,b2.hex từ working directory/parameter đường dẫn. w1 neuron-major 8x6; w2 neuron-major 3x8. quant_params.vh tạo riêng theo model, phải ghép cùng trọng số. Không trộn params và weight từ hai lần train.

Thiết kế dùng chung phép nhân theo FSM; 84 chu kỳ từ cạnh nhận start đến done theo testbench hiện tại. Đây là số chu kỳ mô phỏng; muốn quy đổi ra thời gian phần cứng phải xác minh timing và clock thực tế bằng Gowin. Testbench dùng clock 10ns chỉ để mô phỏng logic, không chứng minh chip chạy 100MHz.
