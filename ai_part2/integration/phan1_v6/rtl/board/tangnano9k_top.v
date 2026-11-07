// =============================================================================
// tangnano9k_top.v - Top cho kit Sipeed Tang Nano 9K (GW1NR-LV9QN88PC6/I5)
// Phien ban tuong lua Ethernet: 2 cong RMII (LAN8720), man OLED I2C, log qua USB-UART.
//
//   Chan  Tin hieu     Huong   Noi voi                     (vi tri tren hang chan, USB-C huong len)
//   52    clk_27m      vao     thach anh 27 MHz tren kit
//   4     rst_n        vao     nut S2 (1,8 V): nhan = reset
//   3     key_n        vao     nut S1 (1,8 V): doi che do chi phat hien <-> chan
//   17    uart_tx      ra      chip USB-UART tren kit -> Laptop trong (115200 8N1)
//   25    oled_sda     2 chieu man OLED SDA                    trai 5
//   26    oled_scl     2 chieu man OLED SCL                    trai 6
//   35    a_ref_clk    vao     LAN8720 A nINT/RETCLK (GCLKT_4) trai 14
//   27    a_crs_dv     vao     LAN8720 A CRS                   trai 7
//   28,29 a_rxd[0..1]  vao     LAN8720 A RX0, RX1              trai 8, 9
//   30    a_tx_en      ra      LAN8720 A TX_EN                 trai 10
//   33,34 a_txd[0..1]  ra      LAN8720 A TX0, TX1              trai 11, 12
//   63    b_ref_clk    vao     LAN8720 B nINT/RETCLK           phai 1
//   77    b_crs_dv     vao     LAN8720 B CRS                   phai 10
//   76,48 b_rxd[0..1]  vao     LAN8720 B RX0, RX1              phai 11, 19
//   49    b_tx_en      ra      LAN8720 B TX_EN                 phai 20
//   31,32 b_txd[0..1]  ra      LAN8720 B TX0, TX1              phai 21, 22
//   10,11,13-16 led_n  ra      6 LED tren kit: luon tat; chi nhap nhay khi CPU loi (trap)
//
// Hien tai cong Ethernet la KHOI GIA (eth_stub): tu tao luu luong theo kich ban de thu toan
// he thong; khi Phan 4 xong, thay eth_stub bang MAC that (giu nguyen cac cong).
// - Reset: tu giu reset ~2,4 ms sau khi nap cau hinh, va khi nhan S2.
// - SELFTEST = 0: bo khoi gia, cong Ethernet nghi. Dung cho buoc kiem tra noi day (do REF_CLK
//   2 module, man OLED, log) va nhe hon nhieu khi tong hop.
// =============================================================================
`timescale 1ns / 1ps
module tangnano9k_top #(
    parameter         FIRMWARE   = "fw/firmware.hex",
    parameter integer SEC_CYCLES   = 27_000_000,
    parameter integer BAUD         = 115_200,   // tang khi mo phong de log ra nhanh
    parameter integer DEBOUNCE_CYC = 270_000,   // chong rung nut ~10 ms; giam khi mo phong
    parameter integer REF_METER    = 1,         // 0: bo bo do REF_CLK sau khi da kiem tra day
    parameter integer SELFTEST   = 1            // 2: MAC Ethernet THAT cua Phan 4 (eth_mac)
                                                // 1: khoi gia eth_stub tu tao luu luong (demo)
                                                // 0: cong Ethernet nghi - ban kiem tra noi day
) (
    input  wire       clk_27m,
    input  wire       rst_n,
    input  wire       key_n,
    output wire       uart_tx,
    inout  wire       oled_sda,
    inout  wire       oled_scl,
    input  wire       a_ref_clk,
    input  wire       a_crs_dv,
    input  wire [1:0] a_rxd,
    output wire       a_tx_en,
    output wire [1:0] a_txd,
    input  wire       b_ref_clk,
    input  wire       b_crs_dv,
    input  wire [1:0] b_rxd,
    output wire       b_tx_en,
    output wire [1:0] b_txd,
    output wire [5:0] led_n
);
    // ---------------------------------------------------------------- Reset
    reg [1:0]  btn_sync = 2'b00;
    reg [15:0] por_cnt  = 16'd0;
    reg        resetn   = 1'b0;

    always @(posedge clk_27m) begin
        btn_sync <= {btn_sync[0], rst_n};
        if (!btn_sync[1]) begin
            por_cnt <= 16'd0;
            resetn  <= 1'b0;
        end else if (por_cnt != 16'hFFFF) begin
            por_cnt <= por_cnt + 16'd1;       // 65535 chu ky ~ 2,4 ms
            resetn  <= 1'b0;
        end else begin
            resetn  <= 1'b1;
        end
    end

    // ---------------------------------------------------------------- OLED: cuc mang ho
    wire scl_low, sda_low;
    assign oled_scl = scl_low ? 1'b0 : 1'bz;
    assign oled_sda = sda_low ? 1'b0 : 1'bz;

    // ---------------------------------------------------------------- Ethernet (Phan 4)
    wire       frm_valid, frm_sof, frm_eof, frm_dir, frm_crc_ok;
    wire [7:0] frm_data;
    wire       verdict_valid, verdict_drop, mac_crc_err, mac_overflow;

    generate
        if (SELFTEST == 2) begin : g_mac
            // MAC Ethernet that cua Phan 4 (noi thang vao 2 module LAN8720)
            eth_mac u_eth (
                .clk (clk_27m), .rst_n (resetn),
                .a_ref_clk (a_ref_clk), .a_crs_dv (a_crs_dv), .a_rxd (a_rxd), .a_tx_en (a_tx_en), .a_txd (a_txd),
                .b_ref_clk (b_ref_clk), .b_crs_dv (b_crs_dv), .b_rxd (b_rxd), .b_tx_en (b_tx_en), .b_txd (b_txd),
                .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
                .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
                .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
                .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow)
            );
        end else if (SELFTEST == 1) begin : g_selftest
            eth_stub #(.SEC_CYCLES(SEC_CYCLES)) u_eth (
                .clk (clk_27m), .rst_n (resetn),
                .a_ref_clk (a_ref_clk), .a_crs_dv (a_crs_dv), .a_rxd (a_rxd), .a_tx_en (a_tx_en), .a_txd (a_txd),
                .b_ref_clk (b_ref_clk), .b_crs_dv (b_crs_dv), .b_rxd (b_rxd), .b_tx_en (b_tx_en), .b_txd (b_txd),
                .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
                .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
                .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
                .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow),
                .phase (), .n_sensor_fwd (), .n_sensor_drop (), .n_atk_fwd (), .n_atk_drop (),
                .n_other_fwd (), .n_other_drop (), .n_no_verdict ()
            );
        end else begin : g_idle
            // chua co MAC: khong co khung nao; firmware van chay POST, OLED, do REF_CLK
            assign frm_valid = 1'b0; assign frm_data = 8'h00; assign frm_sof = 1'b0;
            assign frm_eof = 1'b0;   assign frm_dir = 1'b0;   assign frm_crc_ok = 1'b0;
            assign mac_crc_err = 1'b0; assign mac_overflow = 1'b0;
            assign a_tx_en = 1'b0; assign a_txd = 2'b00; assign b_tx_en = 1'b0; assign b_txd = 2'b00;
        end
    endgenerate

    // ---------------------------------------------------------------- He thong
    wire trap;
    gateway_soc #(
        .CLK_HZ     (27_000_000),
        .BAUD       (BAUD),
        .FIRMWARE   (FIRMWARE),
        .SEC_CYCLES (SEC_CYCLES),
        .DEBOUNCE_CYC (DEBOUNCE_CYC),
        .REF_METER  (REF_METER)
    ) u_soc (
        .clk (clk_27m), .resetn (resetn),
        .uart_txd (uart_tx),
        .btn_pressed (!key_n),
        .oled_scl_low (scl_low), .oled_sda_low (sda_low),
        .oled_scl_in (oled_scl), .oled_sda_in (oled_sda),
        .ref_clk_a (a_ref_clk), .ref_clk_b (b_ref_clk),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof), .frm_eof (frm_eof),
        .frm_dir (frm_dir), .frm_crc_ok (frm_crc_ok),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .mac_crc_err (mac_crc_err), .mac_overflow (mac_overflow),
        .trap (trap)
    );

    // ---------------------------------------------------------------- LED: tat, nhap nhay khi trap
    reg [22:0] blink_cnt = 23'd0;
    always @(posedge clk_27m) blink_cnt <= blink_cnt + 23'd1;
    assign led_n = ~{6{trap & blink_cnt[22]}};
endmodule
