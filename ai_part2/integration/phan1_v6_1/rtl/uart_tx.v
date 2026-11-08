// =============================================================================
// uart_tx.v - Bo phat UART 8N1 don gian (1 start bit, 8 data bit, 1 stop bit)
// Dung tam cho Phan 1 de kiem tra CPU; Phan 4 co the thay bang khoi UART chinh thuc
// mien la giu nguyen giao tiep: start (xung 1 chu ky), data[7:0], busy, tx.
// =============================================================================
`timescale 1ns / 1ps
module uart_tx #(
    parameter integer CLKS_PER_BIT = 234        // 27 MHz / 115200 baud ~ 234
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       start,      // xung 1 chu ky: bat dau gui byte 'data'
    input  wire [7:0] data,
    output reg        busy,       // =1 trong luc dang gui
    output reg        tx          // chan TX, muc nghi = 1
);
    localparam integer CW = $clog2(CLKS_PER_BIT + 1);

    reg [9:0]    shift;           // {stop, data[7:0], start}
    reg [3:0]    bit_idx;         // so bit con lai can gui
    reg [CW-1:0] clk_cnt;

    always @(posedge clk) begin
        if (!resetn) begin
            tx      <= 1'b1;
            busy    <= 1'b0;
            bit_idx <= 4'd0;
            clk_cnt <= {CW{1'b0}};
        end else if (!busy) begin
            if (start) begin
                shift   <= {1'b1, data, 1'b0};
                busy    <= 1'b1;
                bit_idx <= 4'd10;
                clk_cnt <= {CW{1'b0}};
            end
        end else begin
            if (clk_cnt == 0) begin
                if (bit_idx == 0) begin
                    busy <= 1'b0;                     // da gui xong stop bit
                end else begin
                    tx      <= shift[0];
                    shift   <= {1'b1, shift[9:1]};
                    bit_idx <= bit_idx - 4'd1;
                    clk_cnt <= CLKS_PER_BIT - 1;
                end
            end else begin
                clk_cnt <= clk_cnt - 1'b1;
            end
        end
    end
endmodule
