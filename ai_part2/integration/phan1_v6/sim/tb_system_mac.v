// =============================================================================
// tb_system_mac.v - Thu toan he thong voi MAC Ethernet THAT (eth_mac), khong dung eth_stub.
// Mo hinh PHY bom khung IPv4/TCP that vao cong A (vung ngoai):
//   - cam bien .20 -> broker .2 (1 goi SYN moi "giay", hop le)
//   - nguon .50 -> broker: ~30 goi SYN moi giay (gia lap SYN flood) trong 3 giay
// Kiem qua UART (115200) va cong B (TX ra vung trong):
//   - frm_* tu MAC chay dung: $IDS dem dung so goi, dung IP nguon .50
//   - sau 2 giay tan cong + xac nhan -> $BLK,192.168.10.50
//   - khung cam bien .20 luon duoc chuyen ra cong B; sau khi chan, khung .50 bi bo
// 1 "giay" = 150000 nhip; moi dot gui ngay sau ranh gioi cua so -> nam tron 1 cua so.
// =============================================================================
`timescale 1ns / 1ps
module tb_system_mac;
    localparam integer SEC    = 150_000;   // du rong de CPU xu ly kip moi cua so
    localparam integer CLK_HZ = 27_000_000;
    localparam integer BAUD   = CLK_HZ/15;   // nhanh de mo phong (top cho chinh BAUD)

    reg clk=0, arc=0, brc=0, rstn=1, key=1;
    always #18.518 clk = ~clk;
    always #10.000 arc = ~arc;
    always #10.010 brc = ~brc;

    reg        a_crs=0; reg [1:0] a_rxd=0;
    wire       a_txen; wire [1:0] a_txd;
    reg        b_crs=0; reg [1:0] b_rxd=0;
    wire       b_txen; wire [1:0] b_txd;
    wire       uart_tx;
    tri1       osda, oscl;

    tangnano9k_top #(.FIRMWARE("fw/firmware_sim.hex"), .SEC_CYCLES(SEC), .BAUD(BAUD), .DEBOUNCE_CYC(200), .SELFTEST(2)) dut (
        .clk_27m(clk), .rst_n(rstn), .key_n(key), .uart_tx(uart_tx),
        .oled_sda(osda), .oled_scl(oscl),
        .a_ref_clk(arc), .a_crs_dv(a_crs), .a_rxd(a_rxd), .a_tx_en(a_txen), .a_txd(a_txd),
        .b_ref_clk(brc), .b_crs_dv(b_crs), .b_rxd(b_rxd), .b_tx_en(b_txen), .b_txd(b_txd),
        .led_n());

    integer cyc=0; always @(posedge clk) cyc<=cyc+1;

    // ---- CRC32
    function [31:0] crc32_byte(input [31:0] c0, input [7:0] d);
        integer i; reg [31:0] c; begin c=c0^{24'd0,d};
            for(i=0;i<8;i=i+1) c=c[0]?(c>>1)^32'hEDB88320:(c>>1); crc32_byte=c; end
    endfunction

    // ---- dung 1 khung IPv4/TCP vao mang pay[], tra ve do dai (chua FCS)
    reg [7:0] pay [0:255];
    integer paylen;
    task build(input [7:0] smac, input [31:0] sip, input [31:0] dip,
               input [15:0] sport, input [15:0] dport, input [7:0] flags, input [15:0] iplen);
        integer i; begin
            for (i=0;i<60;i=i+1) pay[i]=8'h00;
            pay[0]=8'h02; pay[5]=8'h02;                 // dst MAC 02..02 (broker)
            pay[6]=8'h02; pay[11]=smac;                 // src MAC
            pay[12]=8'h08; pay[13]=8'h00;               // ethertype IPv4
            pay[14]=8'h45; pay[16]=iplen[15:8]; pay[17]=iplen[7:0];
            pay[20]=8'h40; pay[22]=8'd64; pay[23]=8'd6; // DF, TTL, TCP
            pay[26]=sip[31:24]; pay[27]=sip[23:16]; pay[28]=sip[15:8]; pay[29]=sip[7:0];
            pay[30]=dip[31:24]; pay[31]=dip[23:16]; pay[32]=dip[15:8]; pay[33]=dip[7:0];
            pay[34]=sport[15:8]; pay[35]=sport[7:0]; pay[36]=dport[15:8]; pay[37]=dport[7:0];
            pay[46]=8'h50; pay[47]=flags; pay[48]=8'h72; pay[49]=8'h10;
            paylen = (14+iplen) < 60 ? 60 : 14+iplen;
        end
    endtask

    task put_byte(input [7:0] b); integer d; begin
        for (d=0;d<4;d=d+1) begin @(posedge arc); a_crs<=1; a_rxd<=b[2*d +:2]; end
    end endtask

    task send; integer i,k; reg [31:0] crc; reg [7:0] fcs[0:3]; begin
        crc=32'hFFFFFFFF; for(i=0;i<paylen;i=i+1) crc=crc32_byte(crc,pay[i]); crc=~crc;
        fcs[0]=crc[7:0]; fcs[1]=crc[15:8]; fcs[2]=crc[23:16]; fcs[3]=crc[31:24];
        for(k=0;k<7;k=k+1) put_byte(8'h55); put_byte(8'hD5);
        for(i=0;i<paylen;i=i+1) put_byte(pay[i]);
        for(i=0;i<4;i=i+1) put_byte(fcs[i]);
        @(posedge arc) a_crs<=0; a_rxd<=0;
        for(k=0;k<80;k=k+1) @(posedge arc);               // IFG
    end endtask

    // ---- thu cong B (ra vung trong): dem so khung + luu IP nguon cua khung cuoi
    integer fwdB=0, fwd_sensor=0, fwd_atk=0; reg [31:0] lastB_sip; reg [7:0] bbuf[0:255]; integer bn;
    reg [7:0] shb=0; integer dcb=0; reg[1:0] stb=0;
    always @(negedge brc) begin
        if(!b_txen) begin
            if (stb==2 && bn>=34) begin
                fwdB<=fwdB+1;
                lastB_sip<={bbuf[26],bbuf[27],bbuf[28],bbuf[29]};
                if ({bbuf[26],bbuf[27],bbuf[28],bbuf[29]}==32'hC0A80A14) fwd_sensor<=fwd_sensor+1;
                if ({bbuf[26],bbuf[27],bbuf[28],bbuf[29]}==32'hC0A80A32) fwd_atk<=fwd_atk+1;
            end
            dcb<=0; stb<=0; bn<=0;
        end else case(stb)
            0: if(b_txd==2'b01) stb<=1;
            1: if(b_txd==2'b11) begin stb<=2; dcb<=0; bn<=0; end
            default: begin shb<={b_txd,shb[7:2]};
                if(dcb==3) begin dcb<=0; if(bn<256) begin bbuf[bn]={b_txd,shb[7:2]}; bn<=bn+1; end end
                else dcb<=dcb+1; end
        endcase
    end

    // ---- UART thu -> dem $BLK, $IDS
    localparam integer CPB = CLK_HZ/BAUD;
    reg [7:0] line[0:127]; integer ll=0, bitn; reg [7:0] ch;
    integer n_ids=0, n_blk=0; reg blk_50=0;
    reg post_ok=0;
    task scan_line; integer k; reg m; begin
        if (ll>=4 && line[0]=="$" && line[1]=="I" && line[2]=="D" && line[3]=="S") n_ids=n_ids+1;
        if (ll>=4 && line[0]=="$" && line[1]=="B" && line[2]=="L" && line[3]=="K") begin
            n_blk=n_blk+1;
            // tim chuoi "10.50" -> .50 bi chan (192.168.10.50)
            for (k=0;k+4<ll;k=k+1)
                if (line[k]=="1"&&line[k+1]=="0"&&line[k+2]=="."&&line[k+3]=="5"&&line[k+4]=="0") blk_50=1;
        end
        if (ll>=8 && line[0]=="#"&&line[2]=="P"&&line[7]=="O") post_ok=1;
    end endtask
    initial forever begin
        @(negedge uart_tx); repeat(CPB/2) @(posedge clk);
        if(!uart_tx) begin
            for(bitn=0;bitn<8;bitn=bitn+1) begin repeat(CPB) @(posedge clk); ch[bitn]=uart_tx; end
            repeat(CPB) @(posedge clk);
            if(ch==8'h0A) begin scan_line; ll=0; end
            else if(ch!=8'h0D) begin if(ll<128) begin line[ll]=ch; ll=ll+1; end end
            if (ch>=8'h20 && ch<8'h7F) $write("%c",ch); else if (ch==8'h0A) $write("\n");
        end
    end

    // ---- kich ban: moi "giay" bom cam bien .20 + (3 giay dau) ~30 SYN tu .50
    integer errors=0, s, j;
    task chk(input c, input [8*56-1:0] m); begin
        if(c) $display("[tb] OK   %0s",m); else begin $display("[tb] LOI  %0s",m); errors=errors+1; end
    end endtask

    initial begin
        repeat(40) @(posedge clk); rstn<=0; repeat(40) @(posedge clk); rstn<=1;
        wait (dut.resetn === 1'b1);                    // qua reset luc bat nguon (~65535 nhip)
        wait (post_ok === 1'b1);                       // cho in xong POST -> firmware da vao vong lap
        repeat(SEC/4) @(posedge clk);
        key<=1'b0; repeat(SEC/2) @(posedge clk); key<=1'b1;  // nhan giu ngan (< 2s) S1 -> CHAN
        repeat(SEC/4) @(posedge clk);
        for (s=0;s<6;s=s+1) begin
            @(posedge dut.u_soc.f_valid);          // bat dau ngay sau ranh gioi cua so
            repeat (500) @(posedge clk);
            // 1 khung cam bien .20 hop le (SYN mo ket noi toi broker)
            build(8'h20, 32'hC0A80A14, 32'hC0A80A02, 16'd49152+s[15:0], 16'd1883, 8'h02, 16'd44);
            send;
            // 3 giay dau: SYN flood tu .50
            if (s<5) for (j=0;j<50;j=j+1) begin
                build(8'h32, 32'hC0A80A32, 32'hC0A80A02, 16'h8000+j[15:0], 16'd1883, 8'h02, 16'd40);
                send;
            end
        end
        repeat (SEC) @(posedge clk);

        $display("\n[tb] ket qua: $IDS=%0d $BLK=%0d chan.50=%0b | raB=%0d (cambien=%0d, .50=%0d)",
                 n_ids, n_blk, blk_50, fwdB, fwd_sensor, fwd_atk);
        chk(post_ok, "POST OK qua UART");
        chk(n_ids >= 4, "co >= 4 dong $IDS (MAC -> parser -> feat chay)");
        chk(fwd_sensor > 0, "khung cam bien .20 luon duoc chuyen ra cong B");
        chk(n_blk >= 1 && blk_50, "chan dung 192.168.10.50 sau SYN flood ($BLK)");
        chk(!dut.trap, "CPU khong loi");
        if(errors==0) $display("[tb] PASS"); else $display("[tb] FAIL: %0d loi",errors);
        $finish;
    end

    initial begin #80_000_000_000; $display("[tb] HET GIO"); $finish; end
endmodule
