// =============================================================================
// fw_ram.v - RAM firmware 32 bit, ghi theo tung byte, doc dong bo (1 chu ky)
// Viet theo mau chuan de cong cu tong hop suy ra BSRAM (16 KB = 8 khoi tren GW1NR-9).
// Noi dung ban dau nap tu file .hex (moi dong 1 tu 32 bit) bang $readmemh.
// =============================================================================
`timescale 1ns / 1ps
module fw_ram #(
    parameter integer WORDS = 4096,
    parameter         INIT  = "fw/firmware.hex",
    parameter integer AW    = $clog2(WORDS)
) (
    input  wire          clk,
    input  wire          en,        // =1: thuc hien doc (va ghi neu we != 0)
    input  wire [3:0]    we,        // cho phep ghi tung byte
    input  wire [AW-1:0] addr,      // dia chi tu (word)
    input  wire [31:0]   wdata,
    output reg  [31:0]   rdata
);
    reg [31:0] mem [0:WORDS-1];

    initial $readmemh(INIT, mem);

    always @(posedge clk) begin
        if (en) begin
            if (we[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
            if (we[1]) mem[addr][15: 8] <= wdata[15: 8];
            if (we[2]) mem[addr][23:16] <= wdata[23:16];
            if (we[3]) mem[addr][31:24] <= wdata[31:24];
            rdata <= mem[addr];
        end
    end
endmodule
