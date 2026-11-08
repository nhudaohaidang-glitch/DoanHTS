// =============================================================================
// wb_ai_regs.v - Slave Wishbone: thanh ghi cua AI accelerator (0x3000_0000)
// Noi CPU voi loi ai_core (Phan 2, AI v6 6-8-3, 84 chu ky moi lan suy luan).
// Phan 2 KHONG can sua file nay. START chi duoc nhan khi ai_core dang ranh (busy = 0).
//
//   +0x00 STATUS  (R)   bit0 BUSY (tu ai_core), bit1 DONE (dat khi ai_core bao xong,
//                       xoa khi CPU ra lenh START moi)
//   +0x04 CTRL    (W)   ghi bit0 = 1: START (bi bo qua neu dang BUSY)
//                       ghi bit1 = 1: ABORT (thoi cho ket qua, dung khi ai_core bi treo)
//   +0x08 FEAT_LO (R/W) [7:0] f0  [15:8] f1  [23:16] f2  [31:24] f3   (int8)
//   +0x0C FEAT_HI (R/W) [7:0] f4  [15:8] f5
//   +0x10 RESULT  (R)   [1:0] lop: 0 = Binh thuong, 1 = SYN flood, 2 = quet cong doc
//   +0x14 SCORE0  (R)   diem lop 0 (int16 co dau, mo rong dau len 32 bit; khong phai xac suat)
//   +0x18 SCORE1  (R)   diem lop 1
//   +0x1C SCORE2  (R)   diem lop 2
//   +0x20 LAT     (R)   so chu ky tu START den khi ai_core bao done (16 bit, bao hoa)
// =============================================================================
`timescale 1ns / 1ps
module wb_ai_regs (
    input  wire        clk,
    input  wire        rst,
    input  wire        stb,
    input  wire        we,
    input  wire [31:0] adr,
    input  wire [3:0]  sel,
    input  wire [31:0] dat_w,
    output reg  [31:0] dat_r,
    output reg         ack,
    // giao tiep voi ai_core
    output reg         core_start,
    output wire [47:0] core_feat,
    input  wire        core_busy,
    input  wire        core_done,
    input  wire [1:0]  core_class,
    input  wire [47:0] core_scores
);
    reg [31:0] feat_lo;
    reg [15:0] feat_hi;
    reg        done_flag, running;
    reg [1:0]  r_class;
    reg [47:0] r_scores;
    reg [15:0] lat_cnt;
    assign core_feat = {feat_hi, feat_lo};

    always @(posedge clk) begin
        ack        <= 1'b0;
        core_start <= 1'b0;
        if (rst) begin
            feat_lo   <= 32'd0;
            feat_hi   <= 16'd0;
            done_flag <= 1'b0;
            running   <= 1'b0;
            r_class   <= 2'd0;
            r_scores  <= 48'd0;
            lat_cnt   <= 16'd0;
            dat_r     <= 32'd0;
        end else begin
            // ---- ket qua tu ai_core
            if (running && lat_cnt != 16'hFFFF)
                lat_cnt <= lat_cnt + 16'd1;
            if (core_done && running) begin
                running   <= 1'b0;
                done_flag <= 1'b1;
                r_class   <= core_class;
                r_scores  <= core_scores;
            end
            // ---- bus (dat_r = 0 khi khong doc -> gateway_soc chi can OR)
            dat_r <= 32'd0;
            if (stb && !ack) begin
                ack   <= 1'b1;
                case (adr[5:2])
                    4'd0: dat_r <= {30'd0, done_flag, core_busy | running};
                    4'd1: if (we && dat_w[1]) begin
                              running    <= 1'b0;          // ABORT: bo cho ket qua
                          end else if (we && dat_w[0] && !running && !core_busy) begin
                              core_start <= 1'b1;
                              running    <= 1'b1;
                              done_flag  <= 1'b0;
                              lat_cnt    <= 16'd0;
                          end
                    4'd2: begin
                        if (we) begin
                            if (sel[0]) feat_lo[ 7: 0] <= dat_w[ 7: 0];
                            if (sel[1]) feat_lo[15: 8] <= dat_w[15: 8];
                            if (sel[2]) feat_lo[23:16] <= dat_w[23:16];
                            if (sel[3]) feat_lo[31:24] <= dat_w[31:24];
                        end
                        dat_r <= feat_lo;
                    end
                    4'd3: begin
                        if (we) begin
                            if (sel[0]) feat_hi[ 7: 0] <= dat_w[ 7: 0];
                            if (sel[1]) feat_hi[15: 8] <= dat_w[15: 8];
                        end
                        dat_r <= {16'd0, feat_hi};
                    end
                    4'd4: dat_r <= {30'd0, r_class};
                    4'd5: dat_r <= {{16{r_scores[15]}}, r_scores[15: 0]};
                    4'd6: dat_r <= {{16{r_scores[31]}}, r_scores[31:16]};
                    4'd7: dat_r <= {{16{r_scores[47]}}, r_scores[47:32]};
                    4'd8: dat_r <= {16'd0, lat_cnt};
                    default: ;
                endcase
            end
        end
    end
endmodule
