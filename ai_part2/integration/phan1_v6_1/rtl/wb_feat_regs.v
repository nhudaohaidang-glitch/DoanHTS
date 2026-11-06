// =============================================================================
// wb_feat_regs.v - Slave Wishbone: thanh ghi khoi dac trung (0x2000_0000)
// Noi CPU voi feat_core (Phan 3). Phan 3 KHONG can sua file nay.
//
//   +0x00 STATUS      (R)   bit0 READY   = co cua so moi chua doc
//                           bit1 OVERRUN = co cua so bi bo vi CPU chua doc kip (dinh, xoa bang CTRL)
//   +0x04 CTRL        (R/W) ghi bit0 = 1: ACK, da doc xong -> xoa READY
//                           ghi bit1 = 1: xoa OVERRUN
//                           bit8 ENABLE (R/W, mac dinh 1) -> dua sang feat_core
//   +0x08 WIN_ID      (R)   so thu tu cua so (16 bit)
//   +0x0C PKT_CNT     (R)   so goi IPv4 hop le vao vung bao ve        (raw f0, AI v6)
//   +0x10 BYTE_SUM    (R)   tong truong Total Length IPv4 cua cac goi  (de tinh f1)
//   +0x14 SYN_CNT     (R)   so goi TCP SYN=1, ACK=0 ("SYN mo ket noi") (de tinh f2)
//   +0x18 SRC_IP      (R)   so IP nguon khac nhau                       (raw f3)
//   +0x1C DST_IP      (R)   so IP dich khac nhau                        (raw f4)
//   +0x20 DST_PORT    (R)   so cong dich TCP/UDP khac nhau              (raw f5)
//   +0x24 ERR_CNT     (R)   so goi vao bi loai khoi thong ke (phan manh, tran bo dem...)
//   +0x28 SUSPECT_IP  (R)   IP nghi van chon o cua so truoc, vua kiem tra o cua so nay
//   +0x2C CONFIRM_CNT (R)   so goi SYN mo ket noi tu dung SUSPECT_IP trong cua so nay
//   +0x30 PROT_NET    (R/W) mang can bao ve: chi dem goi co (dst & PROT_MASK) == (PROT_NET & PROT_MASK)
//   +0x34 PROT_MASK   (R/W) mac dinh 0 = dem moi goi chieu ngoai -> trong
//
// Khi feat_core phat win_valid: dat READY (neu READY dang = 1 thi dat them OVERRUN).
// Gia tri doc thang tu feat_core, KHONG chot lai (tiet kiem tai nguyen) -> YEU CAU Phan 3:
// feat_core phai giu nguyen moi dau ra tu win_valid nay toi win_valid ke tiep (1 giay).
// CPU doc xong trong vai ms nen luon doc dung 1 cua so, tru khi da bi OVERRUN.
// =============================================================================
`timescale 1ns / 1ps
module wb_feat_regs (
    input  wire        clk,
    input  wire        rst,
    input  wire        stb,
    input  wire        we,
    input  wire [31:0] adr,
    input  wire [31:0] dat_w,
    output reg  [31:0] dat_r,
    output reg         ack,
    // giao tiep voi feat_core
    output wire        core_enable,
    output wire [31:0] prot_net,
    output wire [31:0] prot_mask,
    input  wire        win_valid,
    input  wire [15:0] win_id,
    input  wire [31:0] pkt_cnt,
    input  wire [31:0] byte_sum,
    input  wire [31:0] syn_cnt,
    input  wire [15:0] src_ip_cnt,
    input  wire [15:0] dst_ip_cnt,
    input  wire [15:0] dst_port_cnt,
    input  wire [15:0] err_cnt,
    input  wire [31:0] suspect_ip,
    input  wire [31:0] confirm_cnt
);
    reg        ready, overrun, enable;
    reg [31:0] r_net, r_mask;
    assign core_enable = enable;
    assign prot_net    = r_net;
    assign prot_mask   = r_mask;

    // KHONG chot lai: doc thang dau ra feat_core (feat_core giu nguyen toi win_valid ke tiep).
    // Tiet kiem ~240 thanh ghi + LUT trung chuyen. READY/OVERRUN giu nguyen y nghia.
    wire wr      = stb && !ack && we;
    wire wr_ctrl = wr && (adr[5:2] == 4'd1);

    reg [31:0] rd;
    always @(*) begin
        case (adr[5:2])
            4'd0:  rd = {30'd0, overrun, ready};
            4'd1:  rd = {23'd0, enable, 8'd0};
            4'd2:  rd = {16'd0, win_id};
            4'd3:  rd = pkt_cnt;
            4'd4:  rd = byte_sum;
            4'd5:  rd = syn_cnt;
            4'd6:  rd = {16'd0, src_ip_cnt};
            4'd7:  rd = {16'd0, dst_ip_cnt};
            4'd8:  rd = {16'd0, dst_port_cnt};
            4'd9:  rd = {16'd0, err_cnt};
            4'd10: rd = suspect_ip;
            4'd11: rd = confirm_cnt;
            4'd12: rd = r_net;
            4'd13: rd = r_mask;
            default: rd = 32'd0;
        endcase
    end

    always @(posedge clk) begin
        ack <= 1'b0;
        if (rst) begin
            ready   <= 1'b0;
            overrun <= 1'b0;
            enable  <= 1'b1;
            r_net   <= 32'd0;
            r_mask  <= 32'd0;
            dat_r   <= 32'd0;
        end else begin
            if (stb && !ack) ack <= 1'b1;
            dat_r <= (stb && !ack) ? rd : 32'd0;   // = 0 khi khong doc
            if (wr_ctrl) enable <= dat_w[8];
            if (wr && adr[5:2] == 4'd12) r_net  <= dat_w;
            if (wr && adr[5:2] == 4'd13) r_mask <= dat_w;
            // ---- READY: dat khi co cua so moi, xoa khi CPU ACK; cua so moi den khi READY con 1 -> OVERRUN
            if (win_valid) begin
                if (!ready || (wr_ctrl && dat_w[0])) ready <= 1'b1;
                else                                  overrun <= 1'b1;
            end else if (wr_ctrl && dat_w[0]) begin
                ready <= 1'b0;
            end
            if (wr_ctrl && dat_w[1]) overrun <= 1'b0;
        end
    end
endmodule
