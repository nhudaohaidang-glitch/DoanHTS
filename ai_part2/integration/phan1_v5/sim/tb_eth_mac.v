// =============================================================================
// tb_eth_mac.v - Thu rieng MAC Ethernet Phan 4 (khong co CPU/bo loc that).
// Bo loc duoc thay bang mo hinh don gian: cho qua het, tru khi byte dau du lieu = 0xDD
// (gia lap "bi chan") -> de kiem ca duong cho qua lan duong bo.
// Kiem: khung tu A ra dung o B (nguyen ven ca FCS); CRC sai -> bo; verdict bo -> khong ra;
// khung tu B ra o A.
// =============================================================================
`timescale 1ns / 1ps
module tb_eth_mac;
    reg clk = 0, arc = 0, brc = 0, rstn = 0;
    always #18.518 clk = ~clk;      // 27 MHz
    always #10.000 arc = ~arc;      // 50 MHz cong A
    always #10.010 brc = ~brc;      // 50 MHz cong B (lech nhe)

    reg        a_crs = 0, b_crs = 0;
    reg  [1:0] a_rxd = 0, b_rxd = 0;
    wire       a_txen, b_txen;
    wire [1:0] a_txd, b_txd;
    wire       fv, fsof, feof, fdir, fok;
    wire [7:0] fdata;
    reg        vv = 0, vd = 0;
    wire       crc_err, overflow;

    eth_mac dut (
        .clk(clk), .rst_n(rstn),
        .a_ref_clk(arc), .a_crs_dv(a_crs), .a_rxd(a_rxd), .a_tx_en(a_txen), .a_txd(a_txd),
        .b_ref_clk(brc), .b_crs_dv(b_crs), .b_rxd(b_rxd), .b_tx_en(b_txen), .b_txd(b_txd),
        .frm_valid(fv), .frm_data(fdata), .frm_sof(fsof), .frm_eof(feof),
        .frm_dir(fdir), .frm_crc_ok(fok),
        .verdict_valid(vv), .verdict_drop(vd), .mac_crc_err(crc_err), .mac_overflow(overflow));

    // ---- CRC32 Ethernet (da thuc 0x04C11DB7, dang dao bit)
    function [31:0] crc32_byte(input [31:0] crc, input [7:0] data);
        integer i; reg [31:0] c;
        begin
            c = crc ^ {24'd0, data};
            for (i=0;i<8;i=i+1) c = c[0] ? (c>>1)^32'hEDB88320 : (c>>1);
            crc32_byte = c;
        end
    endfunction

    // ---- gui 1 khung vao 1 cong (them preamble/SFD/FCS). corrupt=1: hong FCS
    task send_frame(input integer port, input integer n, input corrupt);
        integer i, k; reg [31:0] crc; reg [7:0] b; reg [7:0] fcs [0:3];
        begin
            crc = 32'hFFFFFFFF;
            for (i=0;i<n;i=i+1) crc = crc32_byte(crc, tx_payload[i]);
            crc = ~crc;
            fcs[0]=crc[7:0]; fcs[1]=crc[15:8]; fcs[2]=crc[23:16]; fcs[3]=crc[31:24];
            if (corrupt) fcs[0] = fcs[0] ^ 8'hFF;
            // preamble 7x55 + SFD D5
            for (k=0;k<7;k=k+1) put_byte(port, 8'h55);
            put_byte(port, 8'hD5);
            for (i=0;i<n;i=i+1) put_byte(port, tx_payload[i]);
            for (i=0;i<4;i=i+1) put_byte(port, fcs[i]);
            // ha carrier
            if (port==0) begin @(posedge arc) a_crs<=0; a_rxd<=0; end
            else         begin @(posedge brc) b_crs<=0; b_rxd<=0; end
            for (k=0;k<60;k=k+1) begin if (port==0) @(posedge arc); else @(posedge brc); end  // IFG
        end
    endtask

    reg [7:0] tx_payload [0:1599];

    task put_byte(input integer port, input [7:0] b);
        integer d;
        begin
            for (d=0;d<4;d=d+1) begin
                if (port==0) begin @(posedge arc); a_crs<=1; a_rxd<=b[2*d +:2]; end
                else         begin @(posedge brc); b_crs<=1; b_rxd<=b[2*d +:2]; end
            end
        end
    endtask

    // ---- thu khung ra o 1 cong TX (bo preamble/SFD), luu vao rx_*
    integer rxA_n = 0, rxB_n = 0;
    reg [7:0] rxA [0:1599];
    reg [7:0] rxB [0:1599];
    // 2 bo thu rieng - tim SFD o muc dibit (giong rmii_rx), lay mau canh xuong de khong dua TX
    // st: 0 = cho preamble, 1 = trong preamble, 2 = du lieu
    reg [7:0] shA = 0; integer dcA = 0; reg [1:0] stA = 0;
    always @(negedge arc) begin
        if (!a_txen) begin dcA<=0; stA<=0; end
        else case (stA)
            0: if (a_txd==2'b01) stA<=1;
            1: if (a_txd==2'b11) begin stA<=2; dcA<=0; end
            default: begin
                shA <= {a_txd, shA[7:2]};
                if (dcA==3) begin dcA<=0; rxA[rxA_n]={a_txd, shA[7:2]}; rxA_n=rxA_n+1; end
                else dcA<=dcA+1;
            end
        endcase
    end
    reg [7:0] shB = 0; integer dcB = 0; reg [1:0] stB = 0;
    always @(negedge brc) begin
        if (!b_txen) begin dcB<=0; stB<=0; end
        else case (stB)
            0: if (b_txd==2'b01) stB<=1;
            1: if (b_txd==2'b11) begin stB<=2; dcB<=0; end
            default: begin
                shB <= {b_txd, shB[7:2]};
                if (dcB==3) begin dcB<=0; rxB[rxB_n]={b_txd, shB[7:2]}; rxB_n=rxB_n+1; end
                else dcB<=dcB+1;
            end
        endcase
    end

    // ---- mo hinh bo loc: cho qua, tru khi byte du lieu dau = 0xDD thi bao bo
    reg [7:0] first_byte; reg got_first;
    always @(posedge clk) begin
        vv <= 1'b0;
        if (fv && fsof) begin first_byte <= fdata; got_first <= 1'b1; end
        if (feof) begin
            vv <= 1'b1;
            vd <= fdir ? 1'b0 : (first_byte == 8'hDD);   // trong->ngoai luon cho qua
        end
    end

    integer errors = 0, i;
    task chk(input cond, input [8*48-1:0] msg);
        begin if (cond) $display("[tb] OK   %0s", msg);
              else begin $display("[tb] LOI  %0s", msg); errors=errors+1; end end
    endtask

    task load(input [7:0] first, input integer n);
        integer i;
        begin for (i=0;i<n;i=i+1) tx_payload[i] = first + i[7:0]; end
    endtask


    initial begin
        repeat (10) @(posedge clk); rstn <= 1;
        repeat (10) @(posedge clk);

        // 1. khung tot tu A (64 byte du lieu) -> phai ra o B nguyen ven + 4 FCS
        load(8'h10, 64); rxB_n=0;
        send_frame(0, 64, 0);
        repeat (6000) @(posedge clk);
        chk(rxB_n==68, "khung tu A ra o B du 68 byte (64 + 4 FCS)");
        begin : chk1 integer bad; bad=0;
            for (i=0;i<64;i=i+1) if (rxB[i]!==tx_payload[i]) bad=bad+1;
            chk(bad==0, "noi dung khung ra o B khop tung byte");
        end
        chk(rxA_n==0, "khung tu A khong vong lai cong A");

        // 2. khung CRC sai tu A -> bo, dem mac_crc_err, khong ra B
        rxB_n=0; load(8'h20, 64);
        send_frame(0, 64, 1);
        repeat (6000) @(posedge clk);
        chk(rxB_n==0, "khung CRC sai bi bo, khong ra B");

        // 3. verdict bo (byte dau = 0xDD) tu A -> khong ra B
        rxB_n=0; tx_payload[0]=8'hDD; for(i=1;i<64;i=i+1) tx_payload[i]=i[7:0];
        send_frame(0, 64, 0);
        repeat (6000) @(posedge clk);
        chk(rxB_n==0, "khung bi verdict bo khong ra B");

        // 4. khung tu B -> ra o A (trong->ngoai luon cho qua, ke ca byte 0xDD)
        rxA_n=0; tx_payload[0]=8'hDD; for(i=1;i<70;i=i+1) tx_payload[i]=8'h40+i[7:0];
        send_frame(1, 70, 0);
        repeat (7000) @(posedge clk);
        chk(rxA_n==74, "khung tu B ra o A du 74 byte");

        if (errors==0) $display("[tb] PASS"); else $display("[tb] FAIL: %0d loi", errors);
        $finish;
    end
endmodule
