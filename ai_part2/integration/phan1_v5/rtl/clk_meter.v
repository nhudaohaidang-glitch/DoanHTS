// =============================================================================
// clk_meter.v - Do tan so mot clock ngoai (REF_CLK 50 MHz tu LAN8720) bang clock he thong.
//
// Mien ref_clk : bo chia 32 lam bit 'tog' dao trang thai moi 32 chu ky ref_clk.
// Mien clk     : dong bo 'tog' qua 2 flip-flop, dem so lan dao trong GATE_CYCLES chu ky,
//                hz = so lan dao * 32 (do phan giai 32 Hz).
// Chi 1 bit di qua ranh gioi hai mien clock va bit do on dinh >= 32 chu ky ref_clk
// (~17 chu ky clk o 27 MHz), nen dong bo 2 tang la du an toan.
// Khong co module noi vao (chan tha noi): ket qua co the la 0 hoac so ngau nhien nho.
// =============================================================================
`timescale 1ns / 1ps
module clk_meter #(
    parameter integer GATE_CYCLES = 27_000_000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        ref_clk,
    output reg  [31:0] hz
);
    // ---- mien ref_clk
    reg [4:0] pre = 5'd0;
    reg       tog = 1'b0;
    always @(posedge ref_clk) begin
        pre <= pre + 5'd1;
        if (pre == 5'd31) tog <= ~tog;
    end

    // ---- mien clk
    reg [2:0]  s = 3'b000;
    reg [31:0] gate, edges;
    always @(posedge clk) begin
        s <= {s[1:0], tog};
        if (rst) begin
            gate  <= 32'd0;
            edges <= 32'd0;
            hz    <= 32'd0;
        end else if (gate == GATE_CYCLES - 1) begin
            gate  <= 32'd0;
            hz    <= (edges + (s[2] ^ s[1])) << 5;
            edges <= 32'd0;
        end else begin
            gate  <= gate + 32'd1;
            if (s[2] ^ s[1]) edges <= edges + 32'd1;
        end
    end
endmodule
