// =============================================================================
// tb_gateway.v - Testbench toan he thong Phan 1 (tuong lua Ethernet)
//
//   eth_stub (khoi gia Phan 4, tu tao luu luong theo kich ban)
//        |  frm_* / verdict_*
//   gateway_soc (CPU + firmware_sim.hex + AI v6 that cua Phan 2 + khoi gia Phan 3)
//        |  uart_txd -> bo thu UART trong testbench -> sim/out/uart.log
//
// 1 "giay" mo phong = SEC chu ky (thay vi 27 000 000) de chay nhanh; firmware ban mo phong
// (-DSIM_FAST) chan 6 giay thay vi 60. Toc do UART = CLK_HZ / 20.
// Kich ban cua eth_stub (LOOP = 0, giay):
//   [0,2) im lang  [2,5) binh thuong  [5,11) SYN flood tu .50  [11,19) binh thuong
//   [19,24) quet cong tu .51  [24,27) binh thuong  [27,31) SYN flood gia IP  [31,..) binh thuong
// Testbench bam nut S1:
//   sau POST + 0.25 s: nhan 0.6 s -> CHAN (POST V6 co 37 vector)
//   t=25   giu 3.5 giay   -> bat lop 2 (co du thoi gian khi CPU dang in UART)
//   t=33   giu 3.5 giay   -> tat lop 2
//   t=37   nhan ngan      -> ve CHI PHAT HIEN (go het IP dang chan)
// Kiem tra trong testbench: POST OK, CPU khong loi, moi khung deu co verdict, khung cam bien
// khong bao gio bi bo, moi dot tan cong deu co khung bi bo, bo dem phan cung khop eth_stub.
// Kiem tra chi tiet log (checksum, $BLK/$UNB dung IP, dung luc...): tools/check_log.py
// =============================================================================
`timescale 1ns / 1ps
module tb_gateway;
    localparam integer SEC    = 150_000;
    localparam integer CLK_HZ = 27_000_000;
    localparam integer BAUD   = CLK_HZ / 20;
    localparam integer CPB    = CLK_HZ / BAUD;
    localparam integer END_S  = 40;

    reg clk = 1'b0, refa = 1'b0, refb = 1'b0;
    always #18.518 clk  = ~clk;          // 27 MHz
    always #10.000 refa = ~refa;         // 50 MHz
    always #10.002 refb = ~refb;         // 50 MHz lech 0,02 %

    reg resetn = 1'b0;
    reg btn    = 1'b0;

    wire       uart_txd, scl_low, sda_low, trap;
    wire       frm_valid, frm_sof, frm_eof, frm_dir, frm_crc_ok;
    wire [7:0] frm_data;
    wire       verdict_valid, verdict_drop, mac_crc_err, mac_overflow;
    wire [3:0] phase;
    wire [31:0] n_sensor_fwd, n_sensor_drop, n_atk_fwd, n_atk_drop, n_other_fwd, n_other_drop, n_no_verdict;

    // khong gan man OLED trong bai nay: chan duoc keo len, khong ai tra ACK
    // -> firmware phai tu nhan ra "khong co man" va van chay binh thuong (bai tb_oled thu man)
    wire scl_in = !scl_low;
    wire sda_in = !sda_low;

    eth_stub #(.SEC_CYCLES(SEC), .RATE_SYN(400), .RATE_SCAN(250), .RATE_SPOOF(400), .LOOP(0)) u_eth (
        .clk (clk), .rst_n (resetn),
        .a_ref_clk (refa), .a_crs_dv (1'b0), .a_rxd (2'b00), .a_tx_en (), .a_txd (),
        .b_ref_clk (refb), .b_crs_dv (1'b0), .b_rxd (2'b00), .b_tx_en (), .b_txd (),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
        .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow),
        .phase (phase), .n_sensor_fwd (n_sensor_fwd), .n_sensor_drop (n_sensor_drop),
        .n_atk_fwd (n_atk_fwd), .n_atk_drop (n_atk_drop),
        .n_other_fwd (n_other_fwd), .n_other_drop (n_other_drop), .n_no_verdict (n_no_verdict)
    );

    gateway_soc #(
        .CLK_HZ (CLK_HZ), .BAUD (BAUD), .FIRMWARE ("fw/firmware_sim.hex"),
        .DEBOUNCE_CYC (100), .SEC_CYCLES (SEC)
    ) dut (
        .clk (clk), .resetn (resetn), .uart_txd (uart_txd), .btn_pressed (btn),
        .oled_scl_low (scl_low), .oled_sda_low (sda_low), .oled_scl_in (scl_in), .oled_sda_in (sda_in),
        .ref_clk_a (refa), .ref_clk_b (refb),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
        .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow), .trap (trap)
    );

    // ---------------------------------------------------------------- thoi gian (giay mo phong)
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // Capture actual hardware counters, firmware-packed feature bytes and raw
    // accelerator scores. This trace is checked against the frozen Python V6.
    integer trace_fd;
    reg runtime_enabled=0,trace_pending=0;
    reg [31:0] tr_pkt,tr_bytes,tr_syn,tr_src,tr_dst,tr_port,tr_win;
    reg [47:0] tr_feat;
    initial begin
        trace_fd=$fopen("sim/out/v6_feature_trace.csv","w");
        if(!trace_fd)$fatal(1,"cannot open feature trace");
        $fwrite(trace_fd,"win,pkt,bytes,syn,src,dst,ports,feat_hex,score0,score1,score2,class_id\n");
    end
    always @(posedge clk) begin
        if(!resetn)begin runtime_enabled<=0;trace_pending<=0;end
        else begin
            if(dut.stb_feat && dut.wb_we && !dut.ack_feat && dut.wb_adr[5:2]==12)runtime_enabled<=1;
            if(dut.a_start)begin
                trace_pending<=runtime_enabled;
                tr_win<=dut.f_win_id;tr_pkt<=dut.f_pkt;tr_bytes<=dut.f_bytes;tr_syn<=dut.f_syn;
                tr_src<=dut.f_src;tr_dst<=dut.f_dst;tr_port<=dut.f_port;tr_feat<=dut.a_feat;
            end
            if(dut.a_done && trace_pending)begin
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%012h,%0d,%0d,%0d,%0d\n",
                    tr_win,tr_pkt,tr_bytes,tr_syn,tr_src,tr_dst,tr_port,tr_feat,
                    $signed(dut.a_scores[15:0]),$signed(dut.a_scores[31:16]),$signed(dut.a_scores[47:32]),dut.a_class);
                $fflush(trace_fd);trace_pending<=0;
            end
        end
    end

    // ---------------------------------------------------------------- bo thu UART
    integer    logf;
    reg [8*64-1:0] uart_log;
    reg [7:0]  line [0:255];
    integer    llen = 0;
    integer    n_lines = 0, n_ids = 0, n_blk = 0, n_unb = 0, n_mode = 0, n_cnt = 0, n_syn = 0;
    reg        post_ok = 1'b0, post_bad = 1'b0;

    function starts;                      // dong hien tai bat dau bang chuoi s (toi da 9 ky tu)?
        input [8*9-1:0] s;
        input integer   n;
        integer k;
        begin
            starts = (llen >= n);
            for (k = 0; k < n; k = k + 1)
                if (line[k] != s[8*(n-1-k) +: 8]) starts = 1'b0;
        end
    endfunction

    task end_line;
        begin
            n_lines = n_lines + 1;
            if (starts("$IDS", 4))      n_ids  = n_ids + 1;
            if (starts("$BLK", 4))      n_blk  = n_blk + 1;
            if (starts("$UNB", 4))      n_unb  = n_unb + 1;
            if (starts("$MODE", 5))     n_mode = n_mode + 1;
            if (starts("$CNT", 4))      n_cnt  = n_cnt + 1;
            if (starts("$SYN", 4))      n_syn  = n_syn + 1;
            if (starts("# POST OK", 9)) post_ok = 1'b1;
            if (starts("# POST LO", 9)) post_bad = 1'b1;
            llen = 0;
        end
    endtask

    integer   bitn;
    reg [7:0] ch;
    initial begin
        if (!$value$plusargs("log=%s", uart_log)) uart_log = "sim/out/uart.log";
        logf = $fopen(uart_log, "w");
        forever begin
            @(negedge uart_txd);
            repeat (CPB / 2) @(posedge clk);
            if (!uart_txd) begin
                for (bitn = 0; bitn < 8; bitn = bitn + 1) begin
                    repeat (CPB) @(posedge clk);
                    ch[bitn] = uart_txd;
                end
                repeat (CPB) @(posedge clk);          // bit stop
                $fwrite(logf, "%c", ch);
                if (ch == 8'h0A) begin
                    $fflush(logf);
                    end_line;
                end else if (ch != 8'h0D && llen < 256) begin
                    line[llen] = ch;
                    llen = llen + 1;
                end
                if (ch == 8'h0D) $write("   [t=%0d.%03d]", cyc / SEC, (cyc % SEC) * 1000 / SEC);
                if (ch == 8'h0A || (ch >= 8'h20 && ch < 8'h7F)) $write("%c", ch);
            end
        end
    end

    // ---------------------------------------------------------------- nut S1
    task press;
        input integer cycles;
        begin
            btn = 1'b1;
            repeat (cycles) @(posedge clk);
            btn = 1'b0;
        end
    endtask

    // ---------------------------------------------------------------- so khung bi bo theo pha
    reg  [31:0] drop_at [0:8];
    reg  [3:0]  ph_prev = 4'd0;
    integer     k;
    initial for (k = 0; k < 9; k = k + 1) drop_at[k] = 0;
    always @(posedge clk) begin
        ph_prev <= phase;
        if (phase != ph_prev) begin
            drop_at[phase] <= n_atk_drop;           // so khung tan cong bi bo luc bat dau pha
            $display("[tb] t=%0d.%0d s: pha %0d, cam bien qua/bo %0d/%0d, tan cong qua/bo %0d/%0d",
                     cyc / SEC, (cyc % SEC) * 10 / SEC, phase, n_sensor_fwd, n_sensor_drop, n_atk_fwd, n_atk_drop);
        end
    end

    // ---------------------------------------------------------------- dieu khien + kiem tra
    integer errors = 0;
    integer d_syn, d_scan, d_spoof;
    integer stop_s;
    initial if ($value$plusargs("stop=%d", stop_s)) begin   // chay ngan de xem log: +stop=3
        wait (cyc >= SEC * stop_s);
        $display("\n[tb] dung o t=%0d s (+stop), chua kiem tra", stop_s);
        $finish;
    end
    task check;
        input cond;
        input [8*72-1:0] msg;
        begin
            if (cond) $display("[tb] OK   %0s", msg);
            else begin $display("[tb] LOI  %0s", msg); errors = errors + 1; end
        end
    endtask

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("sim/out/tb_gateway.vcd");
            $dumpvars(0, tb_gateway);
        end
        repeat (20) @(posedge clk);
        resetn = 1'b1;

        wait (post_ok); repeat(SEC/4)@(posedge clk); press(SEC*6/10);
        wait (cyc >= SEC * 25);      press(SEC * 35 / 10);
        wait (cyc >= SEC * 33);      press(SEC * 35 / 10);
        wait (cyc >= SEC * 37);      press(SEC * 6 / 10);
        wait (cyc >= SEC * END_S);

        d_syn   = drop_at[3] - drop_at[2];
        d_scan  = drop_at[5] - drop_at[4];
        d_spoof = drop_at[7] - drop_at[6];
        $display("");
        $display("[tb] ===== KET QUA (sau %0d giay mo phong) =====", END_S);
        $display("[tb] khung cam bien: qua %0d, bo %0d | tan cong: qua %0d, bo %0d | khac: qua %0d, bo %0d",
                 n_sensor_fwd, n_sensor_drop, n_atk_fwd, n_atk_drop, n_other_fwd, n_other_drop);
        $display("[tb] bo theo dot: SYN flood %0d, quet cong %0d, SYN gia IP %0d", d_syn, d_scan, d_spoof);
        $display("[tb] bo dem phan cung: qua %0d, bo do danh sach %0d, bo do gioi han SYN %0d",
                 dut.u_filter_regs.c_fwd, dut.u_filter_regs.c_bl, dut.u_filter_regs.c_syn);
        $display("[tb] log: %0d dong, $IDS %0d, $BLK %0d, $UNB %0d, $MODE %0d, $SYN %0d, $CNT %0d",
                 n_lines, n_ids, n_blk, n_unb, n_mode, n_syn, n_cnt);
        check(post_ok && !post_bad,        "POST OK (bus, thanh ghi, 37 vector AI cua Phan 2)");
        check(!trap,                       "CPU khong bi loi (trap)");
        check(n_no_verdict == 0,           "moi khung deu nhan duoc verdict");
        check(n_sensor_drop == 0,          "khung cam bien (192.168.10.20) khong bao gio bi bo");
        check(n_other_drop == 0,           "khung tra loi cua broker va ARP khong bi bo");
        check(d_syn > 0,                   "SYN flood tu .50 bi chan (danh sach chan)");
        check(d_scan > 0,                  "quet cong tu .51 bi chan (danh sach chan)");
        check(d_spoof > 0,                 "SYN gia IP bi gioi han khi bat lop 2");
        check(dut.u_filter_regs.c_syn > 0, "bo dem CNT_DROP_SYN > 0");
        check(n_ids >= END_S - 3,          "moi cua so co 1 dong $IDS");
        check(n_blk >= 2 && n_unb >= 2,    "co $BLK va $UNB (kiem chi tiet bang check_log.py)");
        check(n_mode == 3 && n_syn == 2,   "$MODE x3 (khoi dong, CHAN, PHAT HIEN), $SYN x2");
        check(dut.u_filter_regs.valid == 8'd0, "het mo phong: danh sach chan rong (da go het)");
        if (errors == 0) $display("[tb] PASS");
        else             $display("[tb] FAIL: %0d loi", errors);
        $fclose(logf);
        $fclose(trace_fd);
        $finish;
    end
endmodule
