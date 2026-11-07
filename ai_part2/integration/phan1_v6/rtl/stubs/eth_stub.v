// =============================================================================
// eth_stub.v - KHOI GIA cho Phan 4 (MAC Ethernet RMII 2 cong + bo dem khung)
//
// Khoi gia KHONG dung chan RMII (tx de 0). No tu tao dong khung Ethernet chieu ngoai -> trong
// (va mot it khung tra loi chieu trong -> ngoai) theo kich ban lap lai, dua vao Phan 3 qua dung
// giao tiep frm_* / verdict_* trong tai lieu nhom, roi dem khung duoc cho qua / bi bo theo loai.
// Dung de: (1) thu chinh sach chan cua firmware tren mo phong, (2) chay tu kiem tra tren kit
// khi chua co MAC that (man OLED va log van chay du).
//
// May trong lab (giong tai lieu nhom):
//   Laptop trong (broker)   192.168.10.2   cong 1883
//   May ao cam bien          192.168.10.20  moi giay: ket noi -> CONNECT -> PUBLISH -> ngat (7 goi)
//   Nguon SYN flood          192.168.10.50  SYN 40 byte toi 1883
//   Nguon quet cong          192.168.10.51  SYN 44 byte toi cong 1, 2, 3...
//   SYN flood gia IP         10.x.y.z ngau nhien
//
// Kich ban (giay):  0 IM LANG 2 | 1 BINH THUONG 3 | 2 SYN FLOOD 6 | 3 BINH THUONG 8
//                   4 QUET CONG 5 | 5 BINH THUONG 3 | 6 SYN GIA IP 4 | 7 BINH THUONG 4 -> lap lai
// Moi khung: gui lien tuc 1 byte / chu ky, cho verdict, khoang cach giua 2 lan bat dau khung
// >= MIN_GAP chu ky (182 chu ky o 27 MHz ~ toc do 100 Mbps cua khung nho nhat).
// Khung khong tinh checksum IP/TCP va CRC (frm_crc_ok luon = 1).
//
// Khi Phan 4 xong: thay file nay bang khoi MAC that, GIU NGUYEN cac cong frm_*, verdict_*,
// mac_crc_err, mac_overflow va chan RMII. Cac cong n_* chi de testbench theo doi.
// =============================================================================
`timescale 1ns / 1ps
module eth_stub #(
    parameter integer SEC_CYCLES = 27_000_000,
    parameter integer MIN_GAP    = 182,
    parameter integer RATE_SYN   = 2000,       // goi/giay
    parameter integer RATE_SCAN  = 500,
    parameter integer RATE_SPOOF = 2000,
    parameter integer LOOP       = 1           // 0: dung o pha cuoi (binh thuong) - dung cho mo phong
) (
    input  wire       clk,
    input  wire       rst_n,
    // RMII - khoi gia khong dung
    input  wire       a_ref_clk, input wire a_crs_dv, input wire [1:0] a_rxd,
    output wire       a_tx_en,   output wire [1:0] a_txd,
    input  wire       b_ref_clk, input wire b_crs_dv, input wire [1:0] b_rxd,
    output wire       b_tx_en,   output wire [1:0] b_txd,
    // dong byte khung -> Phan 3
    output reg        frm_valid,
    output reg  [7:0] frm_data,
    output reg        frm_sof,
    output reg        frm_eof,
    output reg        frm_dir,
    output reg        frm_crc_ok,
    input  wire       verdict_valid,
    input  wire       verdict_drop,
    output wire       mac_crc_err,
    output wire       mac_overflow,
    // theo doi
    output reg  [3:0]  phase,
    output reg  [31:0] n_sensor_fwd,
    output reg  [31:0] n_sensor_drop,
    output reg  [31:0] n_atk_fwd,
    output reg  [31:0] n_atk_drop,
    output reg  [31:0] n_other_fwd,
    output reg  [31:0] n_other_drop,
    output reg  [31:0] n_no_verdict
);
    assign a_tx_en = 1'b0; assign a_txd = 2'b00;
    assign b_tx_en = 1'b0; assign b_txd = 2'b00;
    assign mac_crc_err  = 1'b0;
    assign mac_overflow = 1'b0;

    // ---------------------------------------------------------------- kich ban
    localparam [2:0] K_IDLE = 3'd0, K_NORM = 3'd1, K_SYN = 3'd2, K_SCAN = 3'd3, K_SPOOF = 3'd4;
    function [2:0] ph_kind;
        input [3:0] p;
        case (p)
            4'd0: ph_kind = K_IDLE;  4'd1: ph_kind = K_NORM;  4'd2: ph_kind = K_SYN;
            4'd3: ph_kind = K_NORM;  4'd4: ph_kind = K_SCAN;  4'd5: ph_kind = K_NORM;
            4'd6: ph_kind = K_SPOOF; default: ph_kind = K_NORM;
        endcase
    endfunction
    function [4:0] ph_len;
        input [3:0] p;
        case (p)
            4'd0: ph_len = 5'd2;  4'd1: ph_len = 5'd3;  4'd2: ph_len = 5'd6;  4'd3: ph_len = 5'd8;
            4'd4: ph_len = 5'd5;  4'd5: ph_len = 5'd3;  4'd6: ph_len = 5'd4;  default: ph_len = 5'd4;
        endcase
    endfunction

    localparam integer CW = $clog2(SEC_CYCLES + 1);
    reg [CW-1:0] sec_cnt;
    reg [4:0]    ph_sec;
    wire         sec_tick = (sec_cnt == SEC_CYCLES - 1);
    wire [2:0]   kind = ph_kind(phase);

    always @(posedge clk) begin
        if (!rst_n) begin
            sec_cnt <= {CW{1'b0}}; ph_sec <= 5'd0; phase <= 4'd0;
        end else if (sec_tick) begin
            sec_cnt <= {CW{1'b0}};
            if (ph_sec + 5'd1 >= ph_len(phase) && !(LOOP == 0 && phase == 4'd7)) begin
                ph_sec <= 5'd0;
                phase  <= (phase == 4'd7) ? 4'd0 : phase + 4'd1;
            end else begin
                ph_sec <= ph_sec + 5'd1;
            end
        end else begin
            sec_cnt <= sec_cnt + 1'b1;
        end
    end

    // ---------------------------------------------------------------- dong ho cac nguon
    localparam integer I_SENS  = SEC_CYCLES / 8;          // 8 o / giay, 7 goi cam bien + 1 o trong
    localparam integer I_SYN   = SEC_CYCLES / RATE_SYN;
    localparam integer I_SCAN  = SEC_CYCLES / RATE_SCAN;
    localparam integer I_SPOOF = SEC_CYCLES / RATE_SPOOF;
    reg [CW-1:0] t_sens, t_atk;                         // du rong cho 1 giay
    reg        due_sens, due_atk, due_arp, reply_pend;
    reg [2:0]  s_idx;                                     // 0..7 trong chu trinh cam bien
    reg [15:0] s_port;                                    // cong nguon cam bien, tang moi chu trinh
    reg [15:0] scan_port;
    reg [31:0] lfsr;

    wire [CW-1:0] atk_interval = (kind == K_SYN) ? I_SYN : (kind == K_SCAN) ? I_SCAN : I_SPOOF;
    wire        atk_on       = (kind == K_SYN) || (kind == K_SCAN) || (kind == K_SPOOF);
    wire        traffic_on   = (kind != K_IDLE);

    // ---------------------------------------------------------------- mo ta khung dang gui
    reg        d_dir;
    reg [1:0]  d_cls;                 // 0 cam bien, 1 tan cong, 2 khac (tra loi, ARP)
    reg        d_arp;
    reg [7:0]  d_smac, d_dmac;        // byte cuoi dia chi MAC 02:00:00:00:00:xx
    reg [15:0] d_iplen, d_sport, d_dport;
    reg [31:0] d_sip, d_dip;
    reg [7:0]  d_flags;
    reg [3:0]  d_doff;
    reg [10:0] d_flen;                // so byte khung gom 4 byte CRC
    reg [10:0] bi;                    // byte dang gui
    reg [9:0]  gap_cnt;                                 // MIN_GAP phai < 1024

    function [7:0] fbyte;
        input [10:0] i;
        begin
            fbyte = 8'h00;
            if (i <= 11'd5)       fbyte = (i == 11'd0) ? 8'h02 : (i == 11'd5) ? d_dmac : 8'h00;
            else if (i <= 11'd11) fbyte = (i == 11'd6) ? 8'h02 : (i == 11'd11) ? d_smac : 8'h00;
            else if (i == 11'd12) fbyte = 8'h08;
            else if (i == 11'd13) fbyte = d_arp ? 8'h06 : 8'h00;
            else if (d_arp) begin
                case (i)
                    11'd15: fbyte = 8'h01;  11'd16: fbyte = 8'h08;  11'd18: fbyte = 8'h06;
                    11'd19: fbyte = 8'h04;  11'd21: fbyte = 8'h01;  11'd22: fbyte = 8'h02;
                    11'd27: fbyte = d_smac;
                    11'd28: fbyte = d_sip[31:24]; 11'd29: fbyte = d_sip[23:16];
                    11'd30: fbyte = d_sip[15:8];  11'd31: fbyte = d_sip[7:0];
                    11'd38: fbyte = d_dip[31:24]; 11'd39: fbyte = d_dip[23:16];
                    11'd40: fbyte = d_dip[15:8];  11'd41: fbyte = d_dip[7:0];
                    default: fbyte = 8'h00;
                endcase
            end else if (i < 11'd14 + d_iplen) begin
                case (i)
                    11'd14: fbyte = 8'h45;
                    11'd16: fbyte = d_iplen[15:8]; 11'd17: fbyte = d_iplen[7:0];
                    11'd20: fbyte = 8'h40;                          // DF, khong phan manh
                    11'd22: fbyte = 8'd64;  11'd23: fbyte = 8'd6;   // TTL, TCP
                    11'd26: fbyte = d_sip[31:24]; 11'd27: fbyte = d_sip[23:16];
                    11'd28: fbyte = d_sip[15:8];  11'd29: fbyte = d_sip[7:0];
                    11'd30: fbyte = d_dip[31:24]; 11'd31: fbyte = d_dip[23:16];
                    11'd32: fbyte = d_dip[15:8];  11'd33: fbyte = d_dip[7:0];
                    11'd34: fbyte = d_sport[15:8]; 11'd35: fbyte = d_sport[7:0];
                    11'd36: fbyte = d_dport[15:8]; 11'd37: fbyte = d_dport[7:0];
                    11'd46: fbyte = {d_doff, 4'h0};
                    11'd47: fbyte = d_flags;
                    11'd48: fbyte = 8'h72;  11'd49: fbyte = 8'h10;  // cua so TCP
                    default: fbyte = 8'h00;
                endcase
            end
        end
    endfunction

    // dat mo ta khung: cam bien / tra loi / ARP / tan cong
    task set_ip;
        input [1:0]  cls;
        input        dir;
        input [7:0]  smac, dmac;
        input [31:0] sip, dip;
        input [15:0] sport, dport, iplen;
        input [7:0]  flags;
        input        opts;            // 1: SYN co option -> data offset = (iplen-20)/4
        begin
            d_cls <= cls; d_dir <= dir; d_arp <= 1'b0;
            d_smac <= smac; d_dmac <= dmac; d_sip <= sip; d_dip <= dip;
            d_sport <= sport; d_dport <= dport; d_iplen <= iplen; d_flags <= flags;
            d_doff <= opts ? iplen[5:2] - 4'd5 : 4'd5;
            d_flen <= ((iplen + 16'd14 < 16'd60) ? 11'd60 : (iplen[10:0] + 11'd14)) + 11'd4;
        end
    endtask

    localparam [31:0] IP_BROKER = 32'hC0A80A02, IP_SENSOR = 32'hC0A80A14,
                      IP_SYN    = 32'hC0A80A32, IP_SCAN   = 32'hC0A80A33;
    localparam [15:0] MQTT = 16'd1883;

    // ---------------------------------------------------------------- may phat
    localparam [1:0] G_IDLE = 2'd0, G_SEND = 2'd1, G_WAIT = 2'd2, G_GAP = 2'd3;
    reg [1:0] g;
    reg [6:0] wait_cnt;
    reg       v_got, v_drop;            // verdict co the den truoc byte cuoi (vd ARP)

    always @(posedge clk) begin
        frm_valid <= 1'b0; frm_sof <= 1'b0; frm_eof <= 1'b0;
        if (!rst_n) begin
            g <= G_IDLE; bi <= 11'd0; gap_cnt <= 10'd0; wait_cnt <= 7'd0;
            v_got <= 1'b0; v_drop <= 1'b0;
            t_sens <= {CW{1'b0}}; t_atk <= {CW{1'b0}};
            due_sens <= 1'b0; due_atk <= 1'b0; due_arp <= 1'b0; reply_pend <= 1'b0;
            s_idx <= 3'd0; s_port <= 16'd49152; scan_port <= 16'd1;
            lfsr <= 32'h1234_5678;
            frm_dir <= 1'b0; frm_crc_ok <= 1'b1; frm_data <= 8'h00;
            d_cls <= 2'd2; d_dir <= 1'b0; d_arp <= 1'b0;
            n_sensor_fwd <= 32'd0; n_sensor_drop <= 32'd0; n_atk_fwd <= 32'd0; n_atk_drop <= 32'd0;
            n_other_fwd <= 32'd0; n_other_drop <= 32'd0; n_no_verdict <= 32'd0;
        end else begin
            lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            // ---- dong ho nguon
            if (!traffic_on) begin
                t_sens <= {CW{1'b0}}; due_sens <= 1'b0; s_idx <= 3'd0;
            end else if (t_sens >= I_SENS - 1) begin
                t_sens <= {CW{1'b0}}; due_sens <= 1'b1;
            end else begin
                t_sens <= t_sens + 1'b1;
            end
            if (!atk_on) begin
                t_atk <= {CW{1'b0}}; due_atk <= 1'b0;
            end else if (t_atk >= atk_interval - 1) begin
                t_atk <= {CW{1'b0}}; due_atk <= 1'b1;
            end else begin
                t_atk <= t_atk + 1'b1;
            end
            if (sec_tick && traffic_on) due_arp <= 1'b1;
            if ((g == G_SEND || g == G_WAIT) && verdict_valid && !v_got) begin
                v_got  <= 1'b1;
                v_drop <= verdict_drop;
            end

            case (g)
                G_IDLE: begin
                    gap_cnt <= 10'd0;
                    v_got   <= 1'b0;
                    if (reply_pend) begin
                        reply_pend <= 1'b0;
                        set_ip(2'd2, 1'b1, 8'h02, 8'h01, IP_BROKER, IP_SENSOR, MQTT, s_port,
                               (s_idx == 3'd1) ? 16'd60 : 16'd52, (s_idx == 3'd1) ? 8'h12 : 8'h10,
                               s_idx == 3'd1);
                        g <= G_SEND; bi <= 11'd0;
                    end else if (due_sens) begin
                        due_sens <= 1'b0;
                        s_idx <= s_idx + 3'd1;
                        if (s_idx == 3'd7) s_port <= s_port + 16'd1;
                        if (s_idx != 3'd7) begin
                            case (s_idx)
                                3'd0: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd60, 8'h02, 1'b1);
                                3'd1: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd52, 8'h10, 1'b0);
                                3'd2: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd80, 8'h18, 1'b0);
                                3'd3: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd77, 8'h18, 1'b0);
                                3'd4: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd54, 8'h18, 1'b0);
                                3'd5: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd52, 8'h11, 1'b0);
                                default: set_ip(2'd0, 1'b0, 8'h20, 8'h02, IP_SENSOR, IP_BROKER, s_port, MQTT, 16'd52, 8'h10, 1'b0);
                            endcase
                            reply_pend <= (s_idx == 3'd0) || (s_idx == 3'd2) || (s_idx == 3'd3) ||
                                          (s_idx == 3'd4) || (s_idx == 3'd5);
                            g <= G_SEND; bi <= 11'd0;
                        end
                    end else if (due_arp) begin
                        due_arp <= 1'b0;
                        d_cls <= 2'd2; d_dir <= 1'b0; d_arp <= 1'b1;
                        d_smac <= 8'h20; d_dmac <= 8'hFF; d_sip <= IP_SENSOR; d_dip <= IP_BROKER;
                        d_flen <= 11'd64;
                        g <= G_SEND; bi <= 11'd0;
                    end else if (due_atk) begin
                        due_atk <= 1'b0;
                        if (kind == K_SYN)
                            set_ip(2'd1, 1'b0, 8'h01, 8'h02, IP_SYN, IP_BROKER, {1'b1, lfsr[14:0]}, MQTT, 16'd40, 8'h02, 1'b1);
                        else if (kind == K_SCAN) begin
                            set_ip(2'd1, 1'b0, 8'h01, 8'h02, IP_SCAN, IP_BROKER, 16'd40000, scan_port, 16'd44, 8'h02, 1'b1);
                            scan_port <= (scan_port == 16'd1024) ? 16'd1 : scan_port + 16'd1;
                        end else
                            set_ip(2'd1, 1'b0, 8'h01, 8'h02, {8'd10, lfsr[23:0]}, IP_BROKER, {1'b1, lfsr[30:16]}, MQTT, 16'd40, 8'h02, 1'b1);
                        g <= G_SEND; bi <= 11'd0;
                    end
                end
                G_SEND: begin
                    gap_cnt   <= gap_cnt + 10'd1;
                    frm_valid <= 1'b1;
                    frm_data  <= fbyte(bi);
                    frm_sof   <= (bi == 11'd0);
                    frm_eof   <= (bi == d_flen - 11'd1);
                    frm_dir   <= d_dir;
                    frm_crc_ok <= 1'b1;
                    bi <= bi + 11'd1;
                    if (bi == d_flen - 11'd1) begin
                        g <= G_WAIT; wait_cnt <= 7'd0;
                    end
                end
                G_WAIT: begin
                    gap_cnt  <= gap_cnt + 10'd1;
                    wait_cnt <= wait_cnt + 7'd1;
                    if (v_got || verdict_valid || wait_cnt == 7'd100) begin : chot
                        reg vd;
                        vd = v_got ? v_drop : verdict_drop;
                        if (!(v_got || verdict_valid)) n_no_verdict <= n_no_verdict + 32'd1;
                        else if (d_cls == 2'd0) begin
                            if (vd) n_sensor_drop <= n_sensor_drop + 32'd1;
                            else    n_sensor_fwd  <= n_sensor_fwd  + 32'd1;
                        end else if (d_cls == 2'd1) begin
                            if (vd) n_atk_drop <= n_atk_drop + 32'd1;
                            else    n_atk_fwd  <= n_atk_fwd  + 32'd1;
                        end else begin
                            if (vd) n_other_drop <= n_other_drop + 32'd1;
                            else    n_other_fwd  <= n_other_fwd  + 32'd1;
                        end
                        g <= G_GAP;
                    end
                end
                default: begin                     // G_GAP: giu khoang cach toi thieu giua 2 khung
                    gap_cnt <= gap_cnt + 10'd1;
                    if (gap_cnt >= MIN_GAP - 1) g <= G_IDLE;
                end
            endcase
        end
    end
endmodule
