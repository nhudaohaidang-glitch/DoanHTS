// =============================================================================
// async_fifo.v - FIFO bat dong bo 2 mien clock, con tro ma Gray
// Theo dung thiet ke chuan trong bai bao "Simulation and Synthesis Techniques
// for Asynchronous FIFO Design" cua Clifford E. Cummings (SNUG 2002).
//
// Ben ghi (wclk) va ben doc (rclk) la 2 mien clock khac nhau. Con tro chuyen
// qua mien kia duoi dang Gray (moi lan chi doi 1 bit) rồi dong bo 2 nhip, nen
// khong bao gio doc ra gia tri rac khi 2 clock lech pha.
//
//   DSIZE  so bit moi o (vd 11 = 8 data + sof + eof + crc_ok)
//   ASIZE  log2 so o (vd 11 -> 2048 o ~ 1 khung Ethernet lon nhat)
// =============================================================================
`timescale 1ns / 1ps
module async_fifo #(
    parameter integer DSIZE = 11,
    parameter integer ASIZE = 11
) (
    // ben ghi
    input  wire             wclk,
    input  wire             wrst_n,
    input  wire             winc,
    input  wire [DSIZE-1:0] wdata,
    output wire             wfull,
    // ben doc
    input  wire             rclk,
    input  wire             rrst_n,
    input  wire             rinc,
    output wire [DSIZE-1:0] rdata,
    output wire             rempty
);
    localparam integer DEPTH = (1 << ASIZE);

    reg  [DSIZE-1:0] mem [0:DEPTH-1];

    // ---- con tro nhi phan + Gray o moi ben
    reg  [ASIZE:0] wbin, wgray;
    reg  [ASIZE:0] rbin, rgray;
    // ban sao Gray cua ben kia, dong bo 2 nhip
    reg  [ASIZE:0] wq1_rgray, wq2_rgray;
    reg  [ASIZE:0] rq1_wgray, rq2_wgray;

    // ============================================================ ben ghi
    wire [ASIZE:0] wbin_next  = wbin + (winc & ~wfull);
    wire [ASIZE:0] wgray_next = (wbin_next >> 1) ^ wbin_next;
    // day khi Gray tiep theo = Gray doc dao 2 bit cao
    wire wfull_val = (wgray_next ==
                      {~wq2_rgray[ASIZE:ASIZE-1], wq2_rgray[ASIZE-2:0]});
    reg  wfull_r;
    assign wfull = wfull_r;

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            {wbin, wgray} <= 0;
            wfull_r <= 1'b0;
        end else begin
            wbin    <= wbin_next;
            wgray   <= wgray_next;
            wfull_r <= wfull_val;
        end
    end
    always @(posedge wclk) if (winc && !wfull) mem[wbin[ASIZE-1:0]] <= wdata;

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) {wq2_rgray, wq1_rgray} <= 0;
        else         {wq2_rgray, wq1_rgray} <= {wq1_rgray, rgray};
    end

    // ============================================================ ben doc
    wire [ASIZE:0] rbin_next  = rbin + (rinc & ~rempty);
    wire [ASIZE:0] rgray_next = (rbin_next >> 1) ^ rbin_next;
    wire rempty_val = (rgray_next == rq2_wgray);
    reg  rempty_r;
    assign rempty = rempty_r;
    assign rdata  = mem[rbin[ASIZE-1:0]];

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            {rbin, rgray} <= 0;
            rempty_r <= 1'b1;
        end else begin
            rbin     <= rbin_next;
            rgray    <= rgray_next;
            rempty_r <= rempty_val;
        end
    end
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) {rq2_wgray, rq1_wgray} <= 0;
        else         {rq2_wgray, rq1_wgray} <= {rq1_wgray, wgray};
    end
endmodule
