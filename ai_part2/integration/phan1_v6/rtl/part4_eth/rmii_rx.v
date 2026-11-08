// =============================================================================
// rmii_rx.v - Nhan RMII (100 Mbps): 2 bit moi nhip REF_CLK 50 MHz, LSB truoc.
// Bo preamble, tim SFD (0xD5), ghep thanh byte, kiem CRC32.
// Xuat dong byte (mien REF_CLK) gom ca 4 byte FCS; crc_ok bao cung nhip eof.
// Ket thuc khung khi CRS_DV ha xuong 0.
//
//   SAMPLE_NEG = 0: lay mau rxd/crs theo canh LEN REF_CLK (mac dinh)
//   SAMPLE_NEG = 1: lay mau theo canh XUONG - dung khi CNT_CRC_ERR tang lien tuc
//                   (xem muc "Canh lay mau" o tai lieu nhom)
// =============================================================================
`timescale 1ns / 1ps
module rmii_rx #(
    parameter SAMPLE_NEG = 1'b0
) (
    input  wire       ref_clk,
    input  wire       rst_n,
    input  wire       crs_dv,
    input  wire [1:0] rxd,
    output reg        o_valid,      // 1 nhip khi co 1 byte
    output reg  [7:0] o_data,
    output reg        o_sof,
    output reg        o_eof,
    output reg        o_crc_ok,
    output reg        o_crc_err     // xung 1 nhip o cuoi khung neu CRC sai
);
    // ---- CRC32 Ethernet (phan anh bit, poly 0xEDB88320); residual khung dung = 0xDEBB20E3
    function [31:0] crc32_byte;
        input [31:0] crc; input [7:0] data;
        integer i; reg [31:0] c;
        begin
            c = crc ^ {24'd0, data};
            for (i=0;i<8;i=i+1) c = c[0] ? (c>>1)^32'hEDB88320 : (c>>1);
            crc32_byte = c;
        end
    endfunction
    localparam [31:0] CRC_MAGIC = 32'hDEBB20E3;   // residual cua khung dung

    // ---- lay mau dau vao theo canh chon
    reg [1:0] rxd_n;
    reg       crs_n;
    generate
        if (SAMPLE_NEG) begin : g_neg
            always @(negedge ref_clk) begin rxd_n <= rxd; crs_n <= crs_dv; end
        end else begin : g_pos
            always @(posedge ref_clk) begin rxd_n <= rxd; crs_n <= crs_dv; end
        end
    endgenerate

    localparam [1:0] S_IDLE = 2'd0, S_PRE = 2'd1, S_DATA = 2'd2, S_END = 2'd3;
    reg [1:0]  st;
    reg [7:0]  sh;              // ghep 4 dibit -> 1 byte
    reg [1:0]  dcnt;           // so dibit da ghep (0..3)
    reg [31:0] crc;
    reg        have_byte;      // da co it nhat 1 byte (de dat sof)

    wire [7:0] byte_next = {rxd_n, sh[7:2]};          // dibit moi vao bit cao, LSB truoc
    wire [31:0] crc_next = crc32_byte(crc, byte_next);

    always @(posedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; dcnt <= 2'd0; sh <= 8'd0; crc <= 32'hFFFFFFFF;
            have_byte <= 1'b0;
            o_valid <= 1'b0; o_data <= 8'd0; o_sof <= 1'b0; o_eof <= 1'b0;
            o_crc_ok <= 1'b0; o_crc_err <= 1'b0;
        end else begin
            o_valid <= 1'b0; o_sof <= 1'b0; o_eof <= 1'b0; o_crc_err <= 1'b0;
            case (st)
                S_IDLE: begin
                    crc <= 32'hFFFFFFFF; dcnt <= 2'd0; have_byte <= 1'b0;
                    if (crs_n && rxd_n == 2'b01) st <= S_PRE;   // bat dau preamble
                end
                S_PRE: begin
                    if (!crs_n) st <= S_IDLE;
                    else if (rxd_n == 2'b11) begin st <= S_DATA; dcnt <= 2'd0; end  // SFD
                    // con lai van la preamble (2'b01), bo qua
                end
                S_DATA: begin
                    if (!crs_n) begin
                        st <= S_END;
                        o_eof    <= 1'b1;
                        o_crc_ok <= (crc == CRC_MAGIC);
                        o_crc_err <= (crc != CRC_MAGIC);
                        // byte cuoi da phat o nhip truoc; neu dang do dibit thi khung loi -> van bao eof
                    end else begin
                        sh <= {rxd_n, sh[7:2]};
                        if (dcnt == 2'd3) begin
                            dcnt    <= 2'd0;
                            o_valid <= 1'b1;
                            o_data  <= byte_next;
                            o_sof   <= !have_byte;
                            have_byte <= 1'b1;
                            crc     <= crc_next;
                        end else begin
                            dcnt <= dcnt + 2'd1;
                        end
                    end
                end
                default: begin   // S_END: cho CRS ha han roi ve IDLE
                    if (!crs_n) st <= S_IDLE;
                end
            endcase
        end
    end
endmodule
