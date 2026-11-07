// =============================================================================
// wb_uart.v - Slave Wishbone: UART TX (0x1000_0000)
//   +0x00 DATA   (W)  ghi byte thap -> gui di (bo qua neu dang ban)
//   +0x04 STATUS (R)  bit0 = 1 khi dang gui
// =============================================================================
`timescale 1ns / 1ps
module wb_uart #(
    parameter integer CLK_HZ = 27_000_000,
    parameter integer BAUD   = 115_200
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        stb,
    input  wire        we,
    input  wire [31:0] adr,
    input  wire [31:0] dat_w,
    output reg  [31:0] dat_r,
    output reg         ack,
    output wire        txd
);
    reg        tx_start;
    reg  [7:0] tx_data;
    wire       tx_busy;

    uart_tx #(.CLKS_PER_BIT(CLK_HZ / BAUD)) u_tx (
        .clk    (clk),
        .resetn (!rst),
        .start  (tx_start),
        .data   (tx_data),
        .busy   (tx_busy),
        .tx     (txd)
    );

    always @(posedge clk) begin
        ack      <= 1'b0;
        tx_start <= 1'b0;
        dat_r    <= 32'd0;                 // = 0 khi khong doc -> gateway_soc chi can OR
        if (rst) begin
            dat_r <= 32'd0;
        end else if (stb && !ack) begin
            ack   <= 1'b1;
            dat_r <= 32'd0;
            case (adr[3:2])
                2'd0: if (we && !tx_busy) begin
                          tx_data  <= dat_w[7:0];
                          tx_start <= 1'b1;
                      end
                2'd1: dat_r <= {31'd0, tx_busy};
                default: ;
            endcase
        end
    end
endmodule
