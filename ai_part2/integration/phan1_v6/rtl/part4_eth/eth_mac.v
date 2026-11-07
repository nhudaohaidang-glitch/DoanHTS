// =============================================================================
// eth_mac.v - MAC Ethernet 2 cong cho cau noi trong suot (Phan 4).
// Thay cho eth_stub, GIU NGUYEN cac cong frm_* / verdict_* / mac_* voi gateway_soc.
//
//   Cong A = vung ngoai, cong B = vung trong.
//   rmii_rx --(FIFO bat dong bo 50->27)--> bo thu khung -> bo dem khung (BSRAM)
//        -> dua tung khung ra frm_* cho Phan 1/3 -> cho verdict
//        -> neu cho qua: doc bo dem --(FIFO 27->50)--> rmii_tx cong doi dien.
//   Khung tu A chuyen ra B, tu B chuyen ra A. CRC sai -> bo (dem mac_crc_err).
//   Dang xu ly 1 khung thi khung moi den bi bo (dem mac_overflow) - hop ly voi IDS.
//   Moi lan 1 khung: 100 Mbps = 12,5 MB/s, xu ly o 27 MHz (1 byte/nhip) du gap doi.
//   FIFO egress sau san 1 khung lon nhat nen khi day khung ra khong bao gio phai doi.
// =============================================================================
`timescale 1ns / 1ps
module eth_mac #(
    parameter integer BUF_AW       = 11,          // 2^11 = 2048 byte / khung
    parameter         SAMPLE_NEG_A = 1'b0,
    parameter         SAMPLE_NEG_B = 1'b1         // cong B (chan thuong) thuong phai doi canh
) (
    input  wire       clk,                        // 27 MHz he thong
    input  wire       rst_n,
    input  wire       a_ref_clk, input wire a_crs_dv, input wire [1:0] a_rxd,
    output wire       a_tx_en,   output wire [1:0] a_txd,
    input  wire       b_ref_clk, input wire b_crs_dv, input wire [1:0] b_rxd,
    output wire       b_tx_en,   output wire [1:0] b_txd,
    output reg        frm_valid,
    output reg  [7:0] frm_data,
    output reg        frm_sof,
    output reg        frm_eof,
    output reg        frm_dir,
    output reg        frm_crc_ok,
    input  wire       verdict_valid,
    input  wire       verdict_drop,
    output reg        mac_crc_err,
    output reg        mac_overflow
);
    localparam integer DEPTH = (1 << BUF_AW);

    // ================================================================ RX
    wire        rxA_v, rxA_sof, rxA_eof, rxA_ok, rxA_err;
    wire [7:0]  rxA_d;
    wire        rxB_v, rxB_sof, rxB_eof, rxB_ok, rxB_err;
    wire [7:0]  rxB_d;

    rmii_rx #(.SAMPLE_NEG(SAMPLE_NEG_A)) u_rxA (
        .ref_clk(a_ref_clk), .rst_n(rst_n), .crs_dv(a_crs_dv), .rxd(a_rxd),
        .o_valid(rxA_v), .o_data(rxA_d), .o_sof(rxA_sof), .o_eof(rxA_eof),
        .o_crc_ok(rxA_ok), .o_crc_err(rxA_err));
    rmii_rx #(.SAMPLE_NEG(SAMPLE_NEG_B)) u_rxB (
        .ref_clk(b_ref_clk), .rst_n(rst_n), .crs_dv(b_crs_dv), .rxd(b_rxd),
        .o_valid(rxB_v), .o_data(rxB_d), .o_sof(rxB_sof), .o_eof(rxB_eof),
        .o_crc_ok(rxB_ok), .o_crc_err(rxB_err));

    // FIFO ingress (50->27): o = {is_eof, crc_ok, sof, data[7:0]}
    wire        igA_empty, igB_empty;
    wire [10:0] igA_q, igB_q;
    wire        igA_pop = !igA_empty;
    wire        igB_pop = !igB_empty;
    async_fifo #(.DSIZE(11), .ASIZE(5)) u_fifoA (
        .wclk(a_ref_clk), .wrst_n(rst_n), .winc(rxA_v | rxA_eof),
        .wdata({rxA_eof, rxA_ok, rxA_sof, rxA_d}), .wfull(),
        .rclk(clk), .rrst_n(rst_n), .rinc(igA_pop), .rdata(igA_q), .rempty(igA_empty));
    async_fifo #(.DSIZE(11), .ASIZE(5)) u_fifoB (
        .wclk(b_ref_clk), .wrst_n(rst_n), .winc(rxB_v | rxB_eof),
        .wdata({rxB_eof, rxB_ok, rxB_sof, rxB_d}), .wfull(),
        .rclk(clk), .rrst_n(rst_n), .rinc(igB_pop), .rdata(igB_q), .rempty(igB_empty));

    // ================================================================ bo dem khung (BSRAM)
    reg [7:0]        bufA [0:DEPTH-1];
    reg [7:0]        bufB [0:DEPTH-1];
    reg [7:0]        bufA_rd, bufB_rd;

    reg              clrA, clrB;
    reg              ov_A, ov_B;                   // xung bao bo khung vi dang ban

    // ---- bo thu khung cong A
    reg [BUF_AW-1:0] wA, lenA;
    reg              readyA, collectA, okA;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wA<=0; lenA<=0; readyA<=0; collectA<=0; okA<=0; ov_A<=0;
        end else begin
            ov_A <= 1'b0;
            if (clrA) readyA <= 1'b0;
            if (igA_pop) begin
                if (igA_q[10]) begin                       // is_eof
                    if (collectA) begin lenA<=wA; okA<=igA_q[9]; readyA<=1'b1; end
                    collectA <= 1'b0; wA <= 0;             // wA = 0 cho khung sau (sof ghi o 0)
                end else if (igA_q[8]) begin               // sof = byte dau (wA dang = 0)
                    if (!readyA && !clrA) begin
                        collectA<=1'b1; wA<=wA+1'b1;
                    end else ov_A<=1'b1;
                end else if (collectA) begin
                    wA<=wA+1'b1;
                end
            end
        end
    end

    // ---- bo thu khung cong B
    reg [BUF_AW-1:0] wB, lenB;
    reg              readyB, collectB, okB;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wB<=0; lenB<=0; readyB<=0; collectB<=0; okB<=0; ov_B<=0;
        end else begin
            ov_B <= 1'b0;
            if (clrB) readyB <= 1'b0;
            if (igB_pop) begin
                if (igB_q[10]) begin
                    if (collectB) begin lenB<=wB; okB<=igB_q[9]; readyB<=1'b1; end
                    collectB <= 1'b0; wB <= 0;
                end else if (igB_q[8]) begin
                    if (!readyB && !clrB) begin
                        collectB<=1'b1; wB<=wB+1'b1;
                    end else ov_B<=1'b1;
                end else if (collectB) begin
                    wB<=wB+1'b1;
                end
            end
        end
    end

    // Ghi bo dem: khoi rieng, KHONG reset, 1 cong ghi -> Yosys suy ra BSRAM
    wire weA = igA_pop && !igA_q[10] && (igA_q[8] ? (!readyA && !clrA) : collectA);
    wire weB = igB_pop && !igB_q[10] && (igB_q[8] ? (!readyB && !clrB) : collectB);
    always @(posedge clk) if (weA) bufA[wA] <= igA_q[7:0];
    always @(posedge clk) if (weB) bufB[wB] <= igB_q[7:0];

    // doc dong bo tu ridx (chi 1 tang thanh ghi -> tre dung 1 nhip, khop duong ong d_*)
    always @(posedge clk) begin bufA_rd <= bufA[ridx]; bufB_rd <= bufB[ridx]; end
    wire [7:0] rd_byte = cur ? bufB_rd : bufA_rd;

    // ================================================================ FIFO egress (27->50) + TX
    wire        egA_empty, egB_empty;
    wire [8:0]  egA_q, egB_q;
    reg         egA_push, egB_push;
    reg  [8:0]  egA_d, egB_d;
    wire        txA_pop, txB_pop, egA_full, egB_full;
    // FIFO egress nho (64 o): chi lam CDC 27->50; bo day khung cham theo TX (wfull)
    async_fifo #(.DSIZE(9), .ASIZE(6)) u_egA (        // -> TX cong A (khung tu B)
        .wclk(clk), .wrst_n(rst_n), .winc(egA_push), .wdata(egA_d), .wfull(egA_full),
        .rclk(a_ref_clk), .rrst_n(rst_n), .rinc(txA_pop), .rdata(egA_q), .rempty(egA_empty));
    async_fifo #(.DSIZE(9), .ASIZE(6)) u_egB (        // -> TX cong B (khung tu A)
        .wclk(clk), .wrst_n(rst_n), .winc(egB_push), .wdata(egB_d), .wfull(egB_full),
        .rclk(b_ref_clk), .rrst_n(rst_n), .rinc(txB_pop), .rdata(egB_q), .rempty(egB_empty));

    rmii_tx u_txA (.ref_clk(a_ref_clk), .rst_n(rst_n), .f_empty(egA_empty),
                   .f_data(egA_q), .f_pop(txA_pop), .tx_en(a_tx_en), .txd(a_txd));
    rmii_tx u_txB (.ref_clk(b_ref_clk), .rst_n(rst_n), .f_empty(egB_empty),
                   .f_data(egB_q), .f_pop(txB_pop), .tx_en(b_tx_en), .txd(b_txd));

    // ================================================================ trong tai: 1 khung / luot
    localparam [2:0] P_IDLE=3'd0, P_STREAM=3'd1, P_WAIT=3'd2, P_FWD=3'd3, P_DONE=3'd4;
    reg [2:0]        pst;
    reg              cur;                 // 0 = khung cong A, 1 = cong B
    reg              last_served;
    reg [BUF_AW-1:0] ridx, clen;
    reg              cur_ok;
    reg              d_v, d_first, d_last;   // duong ong doc BSRAM tre 1 nhip
    reg              v_got, v_drop;         // chot verdict (co the den khi dang stream)
    reg              fetched;               // P_FWD: da phat dia chi, byte san o nhip sau

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pst<=P_IDLE; cur<=0; last_served<=0; ridx<=0; clen<=0; cur_ok<=0;
            d_v<=0; d_first<=0; d_last<=0; clrA<=0; clrB<=0;
            v_got<=0; v_drop<=0; fetched<=0;
            frm_valid<=0; frm_data<=0; frm_sof<=0; frm_eof<=0; frm_dir<=0; frm_crc_ok<=0;
            egA_push<=0; egB_push<=0; egA_d<=0; egB_d<=0;
            mac_crc_err<=0; mac_overflow<=0;
        end else begin
            frm_valid<=0; frm_sof<=0; frm_eof<=0; frm_crc_ok<=0;
            egA_push<=0; egB_push<=0; clrA<=0; clrB<=0;
            mac_crc_err<=0;
            mac_overflow <= ov_A | ov_B;
            if (verdict_valid && pst != P_IDLE) begin v_got<=1'b1; v_drop<=verdict_drop; end

            case (pst)
                P_IDLE: begin
                    d_v<=0;
                    // chi nhan khung moi khi TX cong doi dien da gui xong khung truoc
                    if (readyA && (!readyB || last_served) && egB_empty) begin
                        cur<=0; cur_ok<=okA; clen<=lenA; ridx<=0; last_served<=0;
                        v_got<=0; fetched<=0; pst<=P_STREAM;
                    end else if (readyB && egA_empty) begin
                        cur<=1; cur_ok<=okB; clen<=lenB; ridx<=0; last_served<=1;
                        v_got<=0; fetched<=0; pst<=P_STREAM;
                    end
                end
                P_STREAM: begin
                    // phat byte da doc o nhip truoc
                    frm_valid  <= d_v;
                    frm_data   <= rd_byte;
                    frm_sof    <= d_v & d_first;
                    frm_eof    <= d_v & d_last;
                    frm_dir    <= cur;
                    frm_crc_ok <= (d_v & d_last) ? cur_ok : 1'b0;
                    if (ridx < clen) begin
                        d_v     <= 1'b1;
                        d_first <= (ridx == 0);
                        d_last  <= (ridx == clen - 1'b1);
                        ridx    <= ridx + 1'b1;
                    end else begin
                        d_v <= 1'b0;
                    end
                    if (d_v & d_last) begin ridx<=0; pst<=P_WAIT; end
                end
                P_WAIT: begin
                    if (v_got) begin
                        if (cur_ok && !v_drop) begin
                            d_v<=0; fetched<=0; pst<=P_FWD;
                        end else begin
                            if (!cur_ok) mac_crc_err<=1'b1;
                            pst<=P_DONE;
                        end
                    end
                end
                P_FWD: begin
                    // doc bo dem BSRAM (tre 1 nhip) -> day tung byte vao FIFO egress nho,
                    // cham theo TX: chi day khi FIFO con cho (khong day thi giu, thu lai).
                    // fetched=0: dang cho byte bufX[ridx] (vua phat dia chi o nhip truoc).
                    // fetched=1: byte da san o rd_byte.
                    if (!fetched) begin
                        fetched <= 1'b1;               // rd_byte se co bufX[ridx] o nhip sau
                    end else begin
                        if (cur ? !egA_full : !egB_full) begin
                            if (cur) begin egA_push<=1'b1; egA_d<={(ridx==clen-1'b1), rd_byte}; end
                            else     begin egB_push<=1'b1; egB_d<={(ridx==clen-1'b1), rd_byte}; end
                            if (ridx == clen - 1'b1) pst <= P_DONE;
                            else begin ridx <= ridx + 1'b1; fetched <= 1'b0; end
                        end
                        // FIFO day -> giu nguyen, cho TX rut bot
                    end
                end
                default: begin   // P_DONE
                    if (cur) clrB<=1'b1; else clrA<=1'b1;
                    pst<=P_IDLE;
                end
            endcase
        end
    end
endmodule
