// =============================================================================
// tb_oled.v - Thu man OLED: firmware_sim.hex + mo hinh SSD1306 tren bus I2C
// 1 "giay" = 1 000 000 chu ky (de man kip ve). Chay 9 giay, bam S1 sang CHAN o t=2,6.
// In noi dung man (doc lai tu anh bang font) o t=2,5 va t=9, roi kiem tra:
//   dong 0 doi tu [PHAT HIEN] sang [CHAN]; co dong "Cua so", "Qua :", "Bo  :";
//   luc cuoi dang chan 192.168.10.50 (SYN flood bat dau o t=5); dong AI = 86 chu ky.
// =============================================================================
`timescale 1ns / 1ps
module tb_oled;
    localparam integer SEC    = 1_000_000;
    localparam integer CLK_HZ = 27_000_000;
    localparam integer BAUD   = CLK_HZ / 20;

    reg clk = 1'b0;
    always #18.518 clk = ~clk;
    reg resetn = 1'b0, btn = 1'b0;

    wire       uart_txd, scl_low, sda_low, trap, oled_ack;
    wire       frm_valid, frm_sof, frm_eof, frm_dir, frm_crc_ok;
    wire [7:0] frm_data;
    wire       verdict_valid, verdict_drop, mac_crc_err, mac_overflow;

    // bus I2C cuc mang ho + dien tro keo len
    wire scl = !scl_low;
    wire sda = !(sda_low || oled_ack);

    ssd1306_model u_oled (.scl (scl), .sda (sda), .sda_low (oled_ack));

    eth_stub #(.SEC_CYCLES(SEC), .RATE_SYN(400), .RATE_SCAN(250), .RATE_SPOOF(400), .LOOP(0)) u_eth (
        .clk (clk), .rst_n (resetn),
        .a_ref_clk (1'b0), .a_crs_dv (1'b0), .a_rxd (2'b00), .a_tx_en (), .a_txd (),
        .b_ref_clk (1'b0), .b_crs_dv (1'b0), .b_rxd (2'b00), .b_tx_en (), .b_txd (),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
        .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow),
        .phase (), .n_sensor_fwd (), .n_sensor_drop (), .n_atk_fwd (), .n_atk_drop (),
        .n_other_fwd (), .n_other_drop (), .n_no_verdict ()
    );

    gateway_soc #(
        .CLK_HZ (CLK_HZ), .BAUD (BAUD), .FIRMWARE ("fw/firmware_sim.hex"),
        .DEBOUNCE_CYC (100), .SEC_CYCLES (SEC)
    ) dut (
        .clk (clk), .resetn (resetn), .uart_txd (uart_txd), .btn_pressed (btn),
        .oled_scl_low (scl_low), .oled_sda_low (sda_low), .oled_scl_in (scl), .oled_sda_in (sda),
        .ref_clk_a (1'b0), .ref_clk_b (1'b0),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
        .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow), .trap (trap)
    );

    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // thoi gian ve 1 dong (tu lenh dat trang toi lenh dat trang ke tiep)
    integer last_line_cyc = 0, max_gap = 0, prev_lines = 0;
    always @(posedge clk) if (u_oled.n_lines != prev_lines) begin
        prev_lines <= u_oled.n_lines;
        last_line_cyc <= cyc;
    end

    // ghep chuoi 21 ky tu cua 1 dong man
    function [8*21-1:0] row;
        input integer p;
        integer c;
        begin
            for (c = 0; c < 21; c = c + 1) row[8*(20-c) +: 8] = u_oled.text[p][c];
        end
    endfunction

    integer errors = 0;
    task check;
        input cond;
        input [8*64-1:0] msg;
        begin
            if (cond) $display("[tb] OK   %0s", msg);
            else begin $display("[tb] LOI  %0s", msg); errors = errors + 1; end
        end
    endtask

    integer t_first;
    initial begin
        repeat (20) @(posedge clk);
        resetn = 1'b1;
        wait (u_oled.n_lines == 8);
        t_first = cyc;
        $display("[tb] ve xong 8 dong dau tien o chu ky %0d (lan ve dau ca man)", t_first);

        wait (cyc >= SEC * 25 / 10);
        $display("[tb] t = 2,5 s, che do chi phat hien:");
        u_oled.print_text;
        check(row(0) == "IDS GW   [PHAT HIEN] ", "dong 0 = 'IDS GW   [PHAT HIEN]'");
        check(row(3) >> (8 * 15) == "Qua : ",  "dong 3 bat dau 'Qua : '");
        check(row(7) == "AI  : 86 chu ky      ", "dong 7 = 'AI  : 86 chu ky'");

        wait (cyc >= SEC * 26 / 10);
        btn = 1'b1; repeat (SEC * 4 / 10) @(posedge clk); btn = 1'b0; // -> CHAN (nhan 0,4 s)

        wait (cyc >= SEC * 9);
        $display("[tb] t = 9 s, che do chan, SYN flood tu .50 dang dien ra:");
        check(u_oled.n_nack == 0, "man luon tra ACK dung dia chi 0x3C");
        u_oled.print_text;
        check(u_oled.display_on, "man dang bat (lenh 0xAF)");
        check(row(0) == "IDS GW        [CHAN] ", "dong 0 = 'IDS GW        [CHAN]'");
        check(row(1) >> (8 * 14) == "Cua so ", "dong 1 bat dau 'Cua so '");
        check(row(4) >> (8 * 15) == "Bo  : ",  "dong 4 bat dau 'Bo  : '");
        check(row(5) == "Chan: 192.168.10.50  ", "dong 5 = 'Chan: 192.168.10.50'");
        check(!trap, "CPU khong loi");
        $display("[tb] %0d lenh, %0d byte anh, %0d lan ve dong", u_oled.n_cmd, u_oled.n_data, u_oled.n_lines);
        if (errors == 0) $display("[tb] PASS");
        else             $display("[tb] FAIL: %0d loi", errors);
        $finish;
    end
endmodule
