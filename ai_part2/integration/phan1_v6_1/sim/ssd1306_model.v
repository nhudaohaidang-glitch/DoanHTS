// =============================================================================
// ssd1306_model.v - Mo hinh man OLED SSD1306 (I2C) cho mo phong
// - Tra ACK khi dung dia chi, nhan chuoi lenh (byte dieu khien 0x00) va du lieu anh (0x40)
// - Hieu lenh dat trang (0xB0..B7), cot (0x00..0x1F), bo qua tham so cua cac lenh cau hinh
// - Luu anh 128 x 64 (8 trang x 128 cot); task print_text doc lai chu bang bang font 5x7
//   (sim/font5x7.hex) va in 8 dong x 21 ky tu, roi luu vao text[] de testbench kiem tra.
// Chi la mo hinh hanh vi de kiem firmware, khong mo ta thoi gian thuc cua chip.
// =============================================================================
`timescale 1ns / 1ps
module ssd1306_model #(
    parameter [6:0] ADDR = 7'h3C
) (
    input  wire scl,          // muc that tren day (da tinh ca keo len)
    input  wire sda,
    output reg  sda_low = 1'b0
);
    reg [7:0] fb [0:1023];
    reg [39:0] glyph [0:94];
    reg [7:0] text [0:7][0:20];
    initial $readmemh("sim/font5x7.hex", glyph);
    integer i;
    initial for (i = 0; i < 1024; i = i + 1) fb[i] = 8'h00;

    reg        active = 1'b0, selected = 1'b0, data_mode = 1'b0, display_on = 1'b0;
    reg [3:0]  bitc = 4'd0;
    reg [7:0]  sh = 8'd0;
    integer    byte_idx = 0, args = 0;
    reg [2:0]  page = 3'd0;
    reg [6:0]  col = 7'd0;
    integer    n_cmd = 0, n_data = 0, n_nack = 0, n_lines = 0;

    always @(negedge sda) if (scl) begin            // START (hoac START lap)
        active <= 1'b1; selected <= 1'b0; bitc <= 4'd0; byte_idx <= 0; sda_low <= 1'b0;
    end
    always @(posedge sda) if (scl) begin            // STOP
        active <= 1'b0; sda_low <= 1'b0;
    end
    always @(posedge scl) if (active && bitc < 4'd8) begin
        sh   <= {sh[6:0], sda};
        bitc <= bitc + 4'd1;
    end

    always @(negedge scl) if (active) begin
        if (bitc == 4'd8) begin                     // vua nhan du 1 byte
            bitc <= 4'd9;
            if (byte_idx == 0) begin
                if (sh[7:1] == ADDR && !sh[0]) begin selected <= 1'b1; sda_low <= 1'b1; end
                else begin n_nack <= n_nack + 1; active <= 1'b0; end
            end else if (selected) begin
                sda_low <= 1'b1;
                if (byte_idx == 1) begin
                    data_mode <= sh[6];             // 0x00 lenh, 0x40 du lieu
                end else if (data_mode) begin
                    fb[{page, col}] <= sh;
                    col <= col + 7'd1;
                    n_data <= n_data + 1;
                end else if (args > 0) begin
                    args <= args - 1;
                end else begin
                    n_cmd <= n_cmd + 1;
                    casez (sh)
                        8'b1011_0???: begin page <= sh[2:0]; n_lines <= n_lines + 1; end
                        8'b0000_????: col <= {col[6:4], sh[3:0]};
                        8'b0001_0???: col <= {sh[2:0], col[3:0]};
                        8'hAE: display_on <= 1'b0;
                        8'hAF: display_on <= 1'b1;
                        8'h20, 8'h81, 8'h8D, 8'hA8, 8'hD3, 8'hD5, 8'hD9, 8'hDA, 8'hDB: args <= 1;
                        8'h21, 8'h22: args <= 2;
                        default: ;
                    endcase
                end
            end
            byte_idx <= byte_idx + 1;
        end else if (bitc == 4'd9) begin            // het xung ACK: tha SDA
            sda_low <= 1'b0;
            bitc    <= 4'd0;
        end
    end

    // doc lai chu tren man: moi o 6 cot (5 cot font + 1 cot trong)
    task print_text;
        integer p, c, g, k, hit;
        reg [39:0] g5;
        begin
            $display("+---------------------+  (man OLED, %0s)", display_on ? "dang bat" : "DANG TAT");
            for (p = 0; p < 8; p = p + 1) begin
                for (c = 0; c < 21; c = c + 1) begin
                    g5 = 40'd0;
                    for (k = 0; k < 5; k = k + 1) g5 = {g5[31:0], fb[p * 128 + c * 6 + k]};
                    hit = 8'h3F;                    // '?' neu khong khop chu nao
                    for (g = 0; g < 95; g = g + 1) if (glyph[g] == g5) hit = g + 32;
                    if (g5 == 40'd0) hit = 8'h20;
                    text[p][c] = hit;
                end
                $write("|");
                for (c = 0; c < 21; c = c + 1) $write("%c", text[p][c]);
                $write("|\n");
            end
            $display("+---------------------+");
        end
    endtask
endmodule
