// =============================================================================
// wb_filter_regs.v - Slave Wishbone: thanh ghi bo loc goi (0x5000_0000)
// Noi CPU voi pkt_filter (Phan 3) va dem su kien tu MAC (Phan 4).
// Phan 3, Phan 4 KHONG can sua file nay.
//
//   +0x00 CTRL         (R/W) bit0 BL_EN  = bat danh sach chan
//                            bit1 SYN_EN = bat gioi han SYN
//                            Khoi dong = 0 (chi phat hien)
//   +0x04 SYN_LIMIT    (R/W) so goi SYN toi da moi giay di vao vung trong (16 bit)
//   +0x08 BL_VALID     (R/W) bit i = 1: o i dang chan
//   +0x10..0x2C BL_IP0..BL_IP7 (W)  IP bi chan, byte dau o bit cao (192.168.10.50 = 0xC0A80A32)
//                            CHI GHI, doc ra 0 (de tiet kiem tai nguyen; firmware tu giu ban sao).
//   Moi lan ghi la ghi ca 32 bit (bo qua sel) - firmware chi ghi tu.
//   +0x40 CNT_FWD      (R)   so khung ngoai -> trong da cho qua.
//                            GHI bat ky gia tri vao day = xoa moi bo dem
//   +0x44 CNT_DROP_BL  (R)   so khung bi bo do danh sach chan
//   +0x48 CNT_DROP_SYN (R)   so khung bi bo do gioi han SYN
//   +0x4C CNT_CRC_ERR  (R)   khung CRC sai, ca 2 cong (tu Phan 4)
//   +0x50 CNT_OVERFLOW (R)   khung bi bo vi bo dem day, ca 2 cong (tu Phan 4)
//
// Cach dung an toan: them o = ghi BL_IPi roi moi bat bit i trong BL_VALID;
//                    go o   = tat bit i truoc.
// =============================================================================
`timescale 1ns / 1ps
module wb_filter_regs #(
    parameter [15:0] SYN_LIMIT_RESET = 16'd200
) (
    input  wire         clk,
    input  wire         rst,
    input  wire         stb,
    input  wire         we,
    input  wire [31:0]  adr,
    input  wire [3:0]   sel,
    input  wire [31:0]  dat_w,
    output reg  [31:0]  dat_r,
    output reg          ack,
    // ra pkt_filter (Phan 3)
    output wire         bl_en,
    output wire         syn_lim_en,
    output wire [15:0]  syn_limit,
    output wire [7:0]   bl_valid,
    output wire [255:0] bl_ip,          // o i nam o bl_ip[32*i +: 32]
    // xung dem (1 chu ky) tu pkt_filter va MAC
    input  wire         inc_fwd,
    input  wire         inc_drop_bl,
    input  wire         inc_drop_syn,
    input  wire         inc_crc_err,
    input  wire         inc_overflow
);
    reg  [1:0]  ctrl;
    reg  [15:0] syn_lim;
    reg  [7:0]  valid;
    reg  [31:0] ip [0:7];
    reg  [31:0] c_fwd, c_bl, c_syn, c_crc, c_ovf;

    assign bl_en      = ctrl[0];
    assign syn_lim_en = ctrl[1];
    assign syn_limit  = syn_lim;
    assign bl_valid   = valid;

    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_ip
            assign bl_ip[32*g +: 32] = ip[g];
        end
    endgenerate

    wire [4:0] r   = adr[6:2];
    wire       acc = stb && !ack;
    wire       wr  = acc && we;
    wire       clr = wr && (r == 5'd16);

    // ---- 8 o IP: CHI GHI (ghi ca 32 bit), khong doc lai -> bo chon doc nho hon nhieu.
    //      Firmware tu giu ban sao IP. Khong can reset: o chi duoc dung khi bit valid = 1.
    integer k;
    always @(posedge clk)
        for (k = 0; k < 8; k = k + 1)
            if (wr && r == (5'd4 + k)) ip[k] <= dat_w;

    // ---- doc lai: 0x00 CTRL, 0x04 SYN_LIMIT, 0x08 BL_VALID, 0x40..0x50 bo dem
    reg [31:0] rd;
    always @(*) begin
        rd = 32'd0;
        if (r[4]) begin
            case (r[2:0])
                3'd0: rd = c_fwd;
                3'd1: rd = c_bl;
                3'd2: rd = c_syn;
                3'd3: rd = c_crc;
                3'd4: rd = c_ovf;
                default: rd = 32'd0;
            endcase
        end else if (r[4:2] == 3'd0) begin
            case (r[1:0])
                2'd0: rd = {30'd0, ctrl};
                2'd1: rd = {16'd0, syn_lim};
                2'd2: rd = {24'd0, valid};
                default: rd = 32'd0;
            endcase
        end
    end

    always @(posedge clk) begin
        ack <= 1'b0;
        if (rst) begin
            ctrl    <= 2'b00;
            syn_lim <= SYN_LIMIT_RESET;
            valid   <= 8'd0;
            c_fwd <= 32'd0; c_bl <= 32'd0; c_syn <= 32'd0; c_crc <= 32'd0; c_ovf <= 32'd0;
            dat_r <= 32'd0;
        end else begin
            // ---- bo dem: xoa uu tien hon dem
            if (clr) begin
                c_fwd <= 32'd0; c_bl <= 32'd0; c_syn <= 32'd0; c_crc <= 32'd0; c_ovf <= 32'd0;
            end else begin
                if (inc_fwd)      c_fwd <= c_fwd + 32'd1;
                if (inc_drop_bl)  c_bl  <= c_bl  + 32'd1;
                if (inc_drop_syn) c_syn <= c_syn + 32'd1;
                if (inc_crc_err)  c_crc <= c_crc + 32'd1;
                if (inc_overflow) c_ovf <= c_ovf + 32'd1;
            end
            if (wr && r == 5'd0) ctrl    <= dat_w[1:0];
            if (wr && r == 5'd1) syn_lim <= dat_w[15:0];
            if (wr && r == 5'd2) valid   <= dat_w[7:0];
            if (acc) ack <= 1'b1;
            dat_r <= acc ? rd : 32'd0;             // = 0 khi khong doc
        end
    end
endmodule
