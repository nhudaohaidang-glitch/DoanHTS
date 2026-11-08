// =============================================================================
// wb_sys.v - Slave Wishbone: khoi he thong (0x4000_0000)
//   +0x00 (bo)         (R)   doc ra 0 - truoc day la LED, da bo trong phien ban Ethernet
//   +0x04 CYCLE        (R)   bo dem chu ky clock 32 bit
//   +0x08 OLED_I2C     (R/W) ghi bit0 = 1: keo SCL xuong 0; bit1 = 1: keo SDA xuong 0
//                            ghi 0 = tha noi, dien tro keo len tren module OLED dua len 1
//                            doc bit0/bit1 = gia tri dang ghi; bit8 = muc that SCL, bit9 = muc that SDA
//   +0x0C BTN          (R)   bit0 = 1 khi dang nhan nut S1 (da dong bo, chong rung ~10 ms)
//   +0x10 ID           (R)   0x5256_3332 ("RV32") - de firmware kiem tra bus
//   +0x14 SCRATCH      (R/W) thanh ghi thu, khong anh huong gi
//   +0x18 REFA_HZ      (R)   so canh REF_CLK cong A dem duoc trong 1 giay gan nhat
//   +0x1C REFB_HZ      (R)   tuong tu cho cong B (dung de kiem tra noi day LAN8720)
//   +0x20 SEC_CYCLES   (R)   so chu ky clock cua 1 "giay" (tham so phan cung; 27 000 000
//                            tren kit, nho hon khi mo phong). Firmware dung de dem giay.
// =============================================================================
`timescale 1ns / 1ps
module wb_sys #(
    parameter integer DEBOUNCE_CYC = 270_000,         // ~10 ms o 27 MHz
    parameter integer SEC_CYCLES   = 27_000_000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        stb,
    input  wire        we,
    input  wire [31:0] adr,
    input  wire [3:0]  sel,
    input  wire [31:0] dat_w,
    output reg  [31:0] dat_r,
    output reg         ack,
    input  wire        btn_pressed,                   // 1 = dang nhan (chua dong bo)
    // OLED I2C kieu cuc mang ho: chi keo xuong 0 hoac tha noi
    output wire        oled_scl_low,
    output wire        oled_sda_low,
    input  wire        oled_scl_in,
    input  wire        oled_sda_in,
    // tan so REF_CLK do duoc (tu clk_meter)
    input  wire [31:0] refa_hz,
    input  wire [31:0] refb_hz
);
    localparam [31:0] SYS_ID = 32'h5256_3332;

    reg [1:0]  i2c_reg;
    reg [31:0] scratch;
    reg [31:0] cycle_cnt;
    assign oled_scl_low = i2c_reg[0];
    assign oled_sda_low = i2c_reg[1];

    // ------------------------------------------------ Bo dem chu ky
    always @(posedge clk) begin
        if (rst) cycle_cnt <= 32'd0;
        else     cycle_cnt <= cycle_cnt + 32'd1;
    end

    // ------------------------------------------------ Dong bo chan I2C doc vao
    reg [1:0] scl_s = 2'b11, sda_s = 2'b11;
    always @(posedge clk) begin
        scl_s <= {scl_s[0], oled_scl_in};
        sda_s <= {sda_s[0], oled_sda_in};
    end

    // ------------------------------------------------ Dong bo + chong rung nut bam
    localparam integer DW = (DEBOUNCE_CYC > 1) ? $clog2(DEBOUNCE_CYC) : 1;
    reg [1:0]    btn_sync = 2'b00;
    reg          btn_state;
    reg [DW-1:0] db_cnt;
    always @(posedge clk) begin
        btn_sync <= {btn_sync[0], btn_pressed};
        if (rst) begin
            btn_state <= 1'b0;
            db_cnt    <= {DW{1'b0}};
        end else if (btn_sync[1] == btn_state) begin
            db_cnt <= {DW{1'b0}};
        end else if (db_cnt == DEBOUNCE_CYC - 1) begin
            btn_state <= btn_sync[1];
            db_cnt    <= {DW{1'b0}};
        end else begin
            db_cnt <= db_cnt + 1'b1;
        end
    end

    // ------------------------------------------------ Thanh ghi
    always @(posedge clk) begin
        ack <= 1'b0;
        if (rst) begin
            i2c_reg <= 2'b00;                         // tha noi ca hai chan
            scratch <= 32'd0;
            dat_r   <= 32'd0;
        end else begin
          dat_r <= 32'd0;                    // = 0 khi khong doc -> gateway_soc chi can OR
          if (stb && !ack) begin
            ack   <= 1'b1;
            case (adr[5:2])
                4'd1: dat_r <= cycle_cnt;
                4'd2: begin
                    if (we && sel[0]) i2c_reg <= dat_w[1:0];
                    dat_r <= {22'd0, sda_s[1], scl_s[1], 6'd0, i2c_reg};
                end
                4'd3: dat_r <= {31'd0, btn_state};
                4'd4: dat_r <= SYS_ID;
                4'd5: begin
                    if (we) begin
                        if (sel[0]) scratch[ 7: 0] <= dat_w[ 7: 0];
                        if (sel[1]) scratch[15: 8] <= dat_w[15: 8];
                        if (sel[2]) scratch[23:16] <= dat_w[23:16];
                        if (sel[3]) scratch[31:24] <= dat_w[31:24];
                    end
                    dat_r <= scratch;
                end
                4'd6: dat_r <= refa_hz;
                4'd7: dat_r <= refb_hz;
                4'd8: dat_r <= SEC_CYCLES;
                default: ;
            endcase
          end
        end
    end
endmodule
