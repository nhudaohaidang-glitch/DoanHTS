// =============================================================================
// tb_board.v - Thu nhanh top cua kit (tangnano9k_top) voi firmware.hex THAT
// (khong phai ban mo phong): UART 115200 baud that, I2C ~90 kHz that, reset tu sinh.
// Chi rut ngan 1 "giay" (SEC_CYCLES = 300 000) de khong phai cho 27 trieu chu ky.
// Kiem tra:
//   - reset tu sinh sau ~65 535 chu ky, CPU chay, dong "# POST OK ..., OLED co" qua UART that
//   - man OLED tren chan 2 chieu (cuc mang ho + dien tro keo len) nhan lenh khoi tao, bat man,
//     ve dong 0 = "IDS GW   [PHAT HIEN]"; do tan so SCL
//   - 6 LED tat (muc 1), khong trap; chan TX cua RMII giu 0 (khoi gia)
// =============================================================================
`timescale 1ns / 1ps
module tb_board;
    localparam integer CPB = 27_000_000 / 115_200;   // 234 chu ky / bit

    reg clk = 1'b0, refa = 1'b0, refb = 1'b0;
    always #18.518 clk  = ~clk;
    always #10.000 refa = ~refa;
    always #10.000 refb = ~refb;
    reg rst_n = 1'b1, key_n = 1'b1;

    wire       uart_tx, a_tx_en, b_tx_en;
    wire [1:0] a_txd, b_txd;
    wire [5:0] led_n;
    tri1       oled_sda, oled_scl;                     // dien tro keo len tren module OLED
    wire       oled_ack;
    assign oled_sda = oled_ack ? 1'b0 : 1'bz;

    ssd1306_model u_oled (.scl (oled_scl), .sda (oled_sda), .sda_low (oled_ack));

    tangnano9k_top #(.FIRMWARE ("fw/firmware.hex"), .SEC_CYCLES (300_000)) dut (
        .clk_27m (clk), .rst_n (rst_n), .key_n (key_n), .uart_tx (uart_tx),
        .oled_sda (oled_sda), .oled_scl (oled_scl),
        .a_ref_clk (refa), .a_crs_dv (1'b0), .a_rxd (2'b00), .a_tx_en (a_tx_en), .a_txd (a_txd),
        .b_ref_clk (refb), .b_crs_dv (1'b0), .b_rxd (2'b00), .b_tx_en (b_tx_en), .b_txd (b_txd),
        .led_n (led_n)
    );

    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---- bo thu UART 115200
    reg [7:0] line [0:127];
    integer   llen = 0, bitn;
    reg [7:0] ch;
    reg       post_ok = 1'b0, oled_seen = 1'b0;
    integer   t_reset = -1;
    always @(posedge dut.resetn) t_reset = cyc;
    initial forever begin
        @(negedge uart_tx);
        repeat (CPB / 2) @(posedge clk);
        if (!uart_tx) begin
            for (bitn = 0; bitn < 8; bitn = bitn + 1) begin
                repeat (CPB) @(posedge clk);
                ch[bitn] = uart_tx;
            end
            repeat (CPB) @(posedge clk);
            if (ch == 8'h0A) begin
                $write("   [chu ky %0d]\n", cyc);
                if (llen > 9 && line[0] == "#" && line[2] == "P" && line[7] == "O" && line[8] == "K") post_ok = 1'b1;
                if (llen > 9 && line[0] == "#" && line[2] == "P") begin : find_oled
                    integer k;
                    for (k = 0; k + 6 < llen; k = k + 1)
                        if (line[k] == "O" && line[k+1] == "L" && line[k+2] == "E" && line[k+3] == "D" &&
                            line[k+5] == "c" && line[k+6] == "o") oled_seen = 1'b1;
                end
                llen = 0;
            end else if (ch != 8'h0D) begin
                if (llen < 128) begin line[llen] = ch; llen = llen + 1; end
                $write("%c", ch);
            end
        end
    end

    // ---- tan so SCL
    integer t_prev = 0, period = 0, n_edge = 0;
    always @(posedge oled_scl) begin
        if (t_prev > 0 && cyc - t_prev < 2000) begin period = period + (cyc - t_prev); n_edge = n_edge + 1; end
        t_prev = cyc;
    end

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

    initial begin
        fork
            wait (u_oled.n_lines >= 2);                  // dong 0 da ve xong, dang ve dong 1
            begin repeat (3_000_000) @(posedge clk); $display("[tb] het thoi gian cho"); end
        join_any
        disable fork;
        u_oled.print_text;
        $display("[tb] reset nha o chu ky %0d; SCL trung binh %0d chu ky/xung = %0d kHz",
                 t_reset, n_edge ? period / n_edge : 0, n_edge ? 27_000 * n_edge / period : 0);
        check(t_reset > 65_000 && t_reset < 70_000, "reset tu sinh ~65 535 chu ky sau khi nap");
        check(post_ok,                     "UART 115200: '# POST OK ...'");
        check(oled_seen,                   "firmware thay man OLED ('OLED co')");
        check(u_oled.display_on,           "man da bat (0xAF)");
        check(row(0) == "IDS GW   [PHAT HIEN] ", "dong 0 = 'IDS GW   [PHAT HIEN]'");
        check(n_edge && 27_000 * n_edge / period >= 50 && 27_000 * n_edge / period <= 400,
              "SCL trong khoang 50..400 kHz");
        check(led_n == 6'b111111,          "6 LED tat");
        check(!dut.trap,                   "CPU khong loi");
        check(!a_tx_en && !b_tx_en,        "khoi gia khong phat ra RMII");
        if (errors == 0) $display("[tb] PASS");
        else             $display("[tb] FAIL: %0d loi", errors);
        $finish;
    end
endmodule
