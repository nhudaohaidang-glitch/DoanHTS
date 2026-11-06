// =============================================================================
// rmii_tx.v - Gui RMII (100 Mbps): 2 bit moi nhip REF_CLK 50 MHz, LSB truoc.
// Phat 7 byte preamble (0x55) + 1 byte SFD (0xD5), roi cac byte cua khung lay tu
// FIFO (da gom san 4 byte FCS cu - cau noi khong sua goi nen khong tinh lai CRC),
// roi giu khoang nghi giua 2 khung (IFG >= 96 bit = 48 dibit).
//
// FIFO moi o: {is_last, data[7:0]}. Keo t_pop de lay byte tiep; t_empty = het byte.
// Bat dau 1 khung khi t_have (co it nhat 1 byte dang cho).
// =============================================================================
`timescale 1ns / 1ps
module rmii_tx (
    input  wire       ref_clk,
    input  wire       rst_n,
    // lay byte tu FIFO egress
    input  wire       f_empty,
    input  wire [8:0] f_data,      // [8] = byte cuoi khung, [7:0] = du lieu
    output reg        f_pop,
    // RMII ra PHY
    output reg        tx_en,
    output reg  [1:0] txd
);
    localparam [2:0] T_IDLE = 3'd0, T_PRE = 3'd1, T_SFD = 3'd2,
                     T_DATA = 3'd3, T_IFG = 3'd4;
    reg [2:0] st;
    reg [7:0] sh;          // byte dang phat (dich 2 bit moi nhip)
    reg [1:0] dcnt;        // dibit trong byte (0..3)
    reg [3:0] pre_cnt;     // dem byte preamble
    reg [5:0] ifg_cnt;     // dem dibit IFG
    reg       last_byte;

    always @(posedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= T_IDLE; sh <= 8'd0; dcnt <= 2'd0; pre_cnt <= 4'd0;
            ifg_cnt <= 6'd0; last_byte <= 1'b0;
            tx_en <= 1'b0; txd <= 2'b00; f_pop <= 1'b0;
        end else begin
            f_pop <= 1'b0;
            case (st)
                T_IDLE: begin
                    tx_en <= 1'b0; txd <= 2'b00;
                    if (!f_empty) begin
                        st <= T_PRE; pre_cnt <= 4'd0; sh <= 8'h55; dcnt <= 2'd0;
                    end
                end
                T_PRE: begin
                    tx_en <= 1'b1; txd <= sh[1:0]; sh <= {2'b00, sh[7:2]};
                    if (dcnt == 2'd3) begin
                        dcnt <= 2'd0;
                        if (pre_cnt == 4'd6) begin st <= T_SFD; sh <= 8'hD5; end
                        else begin pre_cnt <= pre_cnt + 4'd1; sh <= 8'h55; end
                    end else dcnt <= dcnt + 2'd1;
                end
                T_SFD: begin
                    tx_en <= 1'b1; txd <= sh[1:0]; sh <= {2'b00, sh[7:2]};
                    if (dcnt == 2'd3) begin
                        dcnt <= 2'd0;
                        // nap byte du lieu dau tien
                        sh <= f_data[7:0]; last_byte <= f_data[8]; f_pop <= 1'b1;
                        st <= T_DATA;
                    end else dcnt <= dcnt + 2'd1;
                end
                T_DATA: begin
                    tx_en <= 1'b1; txd <= sh[1:0]; sh <= {2'b00, sh[7:2]};
                    if (dcnt == 2'd3) begin
                        dcnt <= 2'd0;
                        if (last_byte) begin
                            st <= T_IFG; ifg_cnt <= 6'd0;
                        end else begin
                            sh <= f_data[7:0]; last_byte <= f_data[8]; f_pop <= 1'b1;
                        end
                    end else dcnt <= dcnt + 2'd1;
                end
                default: begin   // T_IFG
                    tx_en <= 1'b0; txd <= 2'b00;
                    if (ifg_cnt == 6'd47) st <= T_IDLE;   // 48 dibit = 96 bit
                    else ifg_cnt <= ifg_cnt + 6'd1;
                end
            endcase
        end
    end
endmodule
