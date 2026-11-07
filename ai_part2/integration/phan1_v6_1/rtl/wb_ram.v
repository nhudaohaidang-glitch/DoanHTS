// =============================================================================
// wb_ram.v - Slave Wishbone: RAM firmware 16 KB (0x0000_0000)
// Tra ack sau 1 chu ky; du lieu doc co san cung luc voi ack (BSRAM doc dong bo).
// Dia chi vuot qua 16 KB bi lap lai (mirror).
// =============================================================================
`timescale 1ns / 1ps
module wb_ram #(
    parameter integer WORDS = 4096,
    parameter         INIT  = "fw/firmware.hex"
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        stb,
    input  wire        we,
    input  wire [31:0] adr,
    input  wire [3:0]  sel,
    input  wire [31:0] dat_w,
    output wire [31:0] dat_r,
    output reg         ack
);
    localparam integer AW = $clog2(WORDS);

    fw_ram #(.WORDS(WORDS), .INIT(INIT)) u_mem (
        .clk   (clk),
        .en    (stb && !ack),
        .we    (we ? sel : 4'b0000),
        .addr  (adr[AW+1:2]),
        .wdata (dat_w),
        .rdata (dat_r)
    );

    always @(posedge clk) begin
        if (rst) ack <= 1'b0;
        else     ack <= stb && !ack;
    end
endmodule
