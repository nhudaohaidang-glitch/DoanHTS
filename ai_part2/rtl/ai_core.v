`timescale 1ns/1ps
`include "quant_params.vh"
// 6-8-3 MLP, one shared signed MAC. Load memory files from the model working directory.
module ai_core #(
    parameter W1_FILE="w1.hex", B1_FILE="b1.hex", W2_FILE="w2.hex", B2_FILE="b2.hex"
)(
    input wire clk, input wire rst_n, input wire start, input wire [47:0] feat,
    output wire busy, output reg done, output reg [1:0] class_id, output reg [47:0] scores
);
    localparam IDLE=0, HSET=1, HMAC=2, OSET=3, OMAC=4, FINISH=5;
    reg [2:0] state;
    reg [3:0] neuron, idx;
    reg [47:0] captured;
    reg [7:0] hidden [0:7];
    reg signed [15:0] result [0:2];
    reg signed [7:0] w1 [0:47], w2 [0:23];
    reg signed [31:0] b1 [0:7], b2 [0:2];
    reg signed [31:0] accumulator;
    reg signed [8:0] operand;
    reg signed [7:0] weight;
    wire signed [16:0] product = operand * weight;
    wire signed [31:0] total = accumulator + {{15{product[16]}},product};
    assign busy = state != IDLE;
    initial begin
        $readmemh(W1_FILE,w1); $readmemh(B1_FILE,b1);
        $readmemh(W2_FILE,w2); $readmemh(B2_FILE,b2);
    end
    always @* begin
        operand=0; weight=0;
        if (state==HMAC) begin
            operand=$signed({1'b0,captured[idx*8 +: 8]});
            weight=w1[neuron*6+idx];
        end else if (state==OMAC) begin
            operand=$signed({1'b0,hidden[idx]});
            weight=w2[neuron*8+idx];
        end
    end
    function [7:0] relu_quant;
        input signed [31:0] a;
        reg signed [31:0] shifted;
        begin
            shifted=a >>> `SHIFT1;
            if (shifted<0) relu_quant=0;
            else if (shifted>127) relu_quant=127;
            else relu_quant=shifted[7:0];
        end
    endfunction
    function [15:0] score_quant;
        input signed [31:0] a;
        reg signed [31:0] shifted;
        begin
            shifted=a >>> `SHIFT2;
            if (shifted>32767) score_quant=16'h7fff;
            else if (shifted < -32768) score_quant=16'h8000;
            else score_quant=shifted[15:0];
        end
    endfunction
    integer k;
    always @(posedge clk) begin
        done<=0;
        if (!rst_n) begin
            state<=IDLE;neuron<=0;idx<=0;captured<=0;accumulator<=0;
            class_id<=0;scores<=0;
            for(k=0;k<8;k=k+1) hidden[k]<=0;
            for(k=0;k<3;k=k+1) result[k]<=0;
        end else case(state)
            IDLE: if(start) begin captured<=feat;neuron<=0;state<=HSET;end
            HSET: begin accumulator<=b1[neuron];idx<=0;state<=HMAC;end
            HMAC: begin
                accumulator<=total;
                if(idx==5) begin
                    hidden[neuron]<=relu_quant(total);
                    if(neuron==7) begin neuron<=0;state<=OSET;end
                    else begin neuron<=neuron+1'b1;state<=HSET;end
                end else idx<=idx+1'b1;
            end
            OSET: begin accumulator<=b2[neuron];idx<=0;state<=OMAC;end
            OMAC: begin
                accumulator<=total;
                if(idx==7) begin
                    result[neuron]<=score_quant(total);
                    if(neuron==2) state<=FINISH;
                    else begin neuron<=neuron+1'b1;state<=OSET;end
                end else idx<=idx+1'b1;
            end
            FINISH: begin
                scores<={result[2],result[1],result[0]};
                if(result[1]>result[0] && result[1]>=result[2]) class_id<=1;
                else if(result[2]>result[0] && result[2]>result[1]) class_id<=2;
                else class_id<=0;
                done<=1;state<=IDLE;
            end
            default: state<=IDLE;
        endcase
    end
endmodule
