// =============================================================================
// gateway_soc.v - Phan loi cua tuong lua Ethernet (Phan 1: CPU + bus + tich hop)
//
//   PicoRV32 (RV32I) --Wishbone--> giai ma dia chi (4 bit cao) --> 6 slave:
//
//   Dia chi       Slave            File                 Noi toi
//   0x0000_0000   RAM 16 KB        wb_ram.v             firmware + du lieu + ngan xep
//   0x1000_0000   UART TX          wb_uart.v            log len Laptop trong (USB-UART tren kit)
//   0x2000_0000   Dac trung        wb_feat_regs.v  -->  feat_core  (Phan 3)
//   0x3000_0000   AI               wb_ai_regs.v    -->  ai_core    (Phan 2, AI v6)
//   0x4000_0000   He thong         wb_sys.v             nut S1, bo dem, I2C man OLED, do REF_CLK
//   0x5000_0000   Bo loc goi       wb_filter_regs.v -->  pkt_filter (Phan 3)
//   con lai       (khong gan)      -                    doc ra 0, ghi bi bo qua
//
// Duong goi (mien clock he thong):
//   Phan 4 (MAC) --frm_*--> pkt_parser --ban ghi header--> feat_core  (thong ke, IP nghi van)
//                                                      \-> pkt_filter --verdict_*--> Phan 4
// CPU khong cham vao tung goi: chi doc thong ke moi cua so, goi AI, ghi luat chan.
// Phan 4 nam ngoai khoi nay (o top cua kit / testbench) de thay the de dang.
// =============================================================================
`timescale 1ns / 1ps
module gateway_soc #(
    parameter integer CLK_HZ       = 27_000_000,
    parameter integer BAUD         = 115_200,
    parameter integer MEM_WORDS    = 4096,           // 16 KB
    parameter         FIRMWARE     = "fw/firmware.hex",
    parameter integer DEBOUNCE_CYC = 270_000,        // chong rung nut ~10 ms
    parameter integer SEC_CYCLES   = 27_000_000,     // 1 "giay" = 1 cua so dac trung
    parameter integer REF_METER    = 1               // 0: bo 2 bo do REF_CLK (tiet kiem ~370 o logic)
) (
    input  wire       clk,
    input  wire       resetn,
    // log
    output wire       uart_txd,
    // nut S1 (1 = dang nhan)
    input  wire       btn_pressed,
    // man OLED I2C, kieu cuc mang ho
    output wire       oled_scl_low,
    output wire       oled_sda_low,
    input  wire       oled_scl_in,
    input  wire       oled_sda_in,
    // REF_CLK cua 2 module LAN8720 (chi de do tan so khi kiem tra noi day)
    input  wire       ref_clk_a,
    input  wire       ref_clk_b,
    // tu Phan 4: dong byte khung (mien clk)
    input  wire       frm_valid,
    input  wire [7:0] frm_data,
    input  wire       frm_sof,
    input  wire       frm_eof,
    input  wire       frm_dir,
    input  wire       frm_crc_ok,
    // ve Phan 4: quyet dinh cho moi khung
    output wire       verdict_valid,
    output wire       verdict_drop,
    // xung dem tu Phan 4
    input  wire       mac_crc_err,
    input  wire       mac_overflow,
    // CPU loi
    output wire       trap
);
    wire rst = !resetn;

    // ================================================================ CPU (Wishbone master)
    wire [31:0] wb_adr, wb_dat_w;
    wire [31:0] wb_dat_r;
    wire [3:0]  wb_sel;
    wire        wb_we, wb_stb, wb_cyc;
    wire        wb_ack;

    picorv32_wb #(
        .ENABLE_COUNTERS   (0),
        .ENABLE_COUNTERS64 (0),
        .ENABLE_MUL        (0),     // khong dung nhan/chia phan cung: tiet kiem LUT
        .ENABLE_DIV        (0),
        .ENABLE_IRQ        (0),
        .COMPRESSED_ISA    (0),
        .CATCH_MISALIGN    (0),     // gcc rv32i luon truy cap thang hang: bo mach bat loi lech
        .PROGADDR_RESET    (32'h0000_0000)
    ) u_cpu (
        .trap      (trap),
        .wb_rst_i  (rst),
        .wb_clk_i  (clk),
        .wbm_adr_o (wb_adr),
        .wbm_dat_o (wb_dat_w),
        .wbm_dat_i (wb_dat_r),
        .wbm_we_o  (wb_we),
        .wbm_sel_o (wb_sel),
        .wbm_stb_o (wb_stb),
        .wbm_ack_i (wb_ack),
        .wbm_cyc_o (wb_cyc),
        .pcpi_valid (), .pcpi_insn (), .pcpi_rs1 (), .pcpi_rs2 (),
        .pcpi_wr    (1'b0), .pcpi_rd (32'd0), .pcpi_wait (1'b0), .pcpi_ready (1'b0),
        .irq        (32'd0), .eoi (),
        .trace_valid (), .trace_data (),
        .mem_instr  ()
    );

    // ================================================================ Giai ma dia chi
    wire       req        = wb_cyc && wb_stb;
    wire [3:0] region     = wb_adr[31:28];
    wire       stb_ram    = req && (region == 4'h0);
    wire       stb_uart   = req && (region == 4'h1);
    wire       stb_feat   = req && (region == 4'h2);
    wire       stb_ai     = req && (region == 4'h3);
    wire       stb_sys    = req && (region == 4'h4);
    wire       stb_filter = req && (region == 4'h5);
    wire       stb_none   = req && (region > 4'h5);

    wire [31:0] dr_ram, dr_uart, dr_feat, dr_ai, dr_sys, dr_filter;
    wire        ack_ram, ack_uart, ack_feat, ack_ai, ack_sys, ack_filter;
    reg         ack_none;

    always @(posedge clk) begin                      // vung khong gan: van tra ack de CPU khong treo
        if (rst) ack_none <= 1'b0;
        else     ack_none <= stb_none && !ack_none;
    end

    assign wb_ack   = ack_ram | ack_uart | ack_feat | ack_ai | ack_sys | ack_filter | ack_none;
    // Cac slave (tru RAM) tu tra 0 khi khong duoc doc -> chi can OR, khong can bo chon 6 duong
    assign wb_dat_r = ack_ram ? dr_ram : (dr_uart | dr_feat | dr_ai | dr_sys | dr_filter);

    // ================================================================ Slave
    wb_ram #(.WORDS(MEM_WORDS), .INIT(FIRMWARE)) u_ram (
        .clk (clk), .rst (rst), .stb (stb_ram), .we (wb_we), .adr (wb_adr),
        .sel (wb_sel), .dat_w (wb_dat_w), .dat_r (dr_ram), .ack (ack_ram)
    );

    wb_uart #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_uart (
        .clk (clk), .rst (rst), .stb (stb_uart), .we (wb_we), .adr (wb_adr),
        .dat_w (wb_dat_w), .dat_r (dr_uart), .ack (ack_uart), .txd (uart_txd)
    );

    wire [31:0] refa_hz, refb_hz;
    generate
        if (REF_METER != 0) begin : g_meter
            clk_meter #(.GATE_CYCLES(SEC_CYCLES)) u_meter_a (.clk (clk), .rst (rst), .ref_clk (ref_clk_a), .hz (refa_hz));
            clk_meter #(.GATE_CYCLES(SEC_CYCLES)) u_meter_b (.clk (clk), .rst (rst), .ref_clk (ref_clk_b), .hz (refb_hz));
        end else begin : g_nometer
            assign refa_hz = 32'd0;            // firmware se in "REF_CLK ... LOI" - binh thuong khi da tat
            assign refb_hz = 32'd0;
        end
    endgenerate

    wb_sys #(.DEBOUNCE_CYC(DEBOUNCE_CYC), .SEC_CYCLES(SEC_CYCLES)) u_sys (
        .clk (clk), .rst (rst), .stb (stb_sys), .we (wb_we), .adr (wb_adr),
        .sel (wb_sel), .dat_w (wb_dat_w), .dat_r (dr_sys), .ack (ack_sys),
        .btn_pressed (btn_pressed),
        .oled_scl_low (oled_scl_low), .oled_sda_low (oled_sda_low),
        .oled_scl_in (oled_scl_in), .oled_sda_in (oled_sda_in),
        .refa_hz (refa_hz), .refb_hz (refb_hz)
    );

    // ---------------------------------------------------------------- Phan 3: tach header
    wire        h_valid, h_dir, h_ipv4, h_frag, h_l4;
    wire [31:0] h_src, h_dst;
    wire [7:0]  h_proto, h_flags;
    wire [15:0] h_len, h_sport, h_dport;

    pkt_parser u_parser (
        .clk (clk), .rst_n (resetn),
        .frm_valid (frm_valid), .frm_data (frm_data), .frm_sof (frm_sof),
        .frm_eof (frm_eof), .frm_dir (frm_dir),
        .hdr_valid (h_valid), .hdr_dir (h_dir), .is_ipv4 (h_ipv4), .hdr_frag (h_frag), .hdr_l4 (h_l4),
        .src_ip (h_src), .dst_ip (h_dst), .ip_proto (h_proto), .ip_len (h_len),
        .src_port (h_sport), .dst_port (h_dport), .tcp_flags (h_flags)
    );

    // ---------------------------------------------------------------- Phan 3: dac trung
    wire        f_enable, f_valid;
    wire [31:0] f_net, f_mask;
    wire [15:0] f_win_id, f_src, f_dst, f_port, f_err;
    wire [31:0] f_pkt, f_bytes, f_syn, f_susp, f_conf;

    wb_feat_regs u_feat_regs (
        .clk (clk), .rst (rst), .stb (stb_feat), .we (wb_we), .adr (wb_adr),
        .dat_w (wb_dat_w), .dat_r (dr_feat), .ack (ack_feat),
        .core_enable (f_enable), .prot_net (f_net), .prot_mask (f_mask),
        .win_valid (f_valid), .win_id (f_win_id),
        .pkt_cnt (f_pkt), .byte_sum (f_bytes), .syn_cnt (f_syn),
        .src_ip_cnt (f_src), .dst_ip_cnt (f_dst), .dst_port_cnt (f_port), .err_cnt (f_err),
        .suspect_ip (f_susp), .confirm_cnt (f_conf)
    );

    feat_core #(.WINDOW_CYCLES(SEC_CYCLES)) u_feat (
        .clk (clk), .rst_n (resetn), .enable (f_enable),
        .prot_net (f_net), .prot_mask (f_mask),
        .hdr_valid (h_valid), .hdr_dir (h_dir), .is_ipv4 (h_ipv4), .hdr_frag (h_frag), .hdr_l4 (h_l4),
        .src_ip (h_src), .dst_ip (h_dst), .ip_proto (h_proto), .ip_len (h_len),
        .src_port (h_sport), .dst_port (h_dport), .tcp_flags (h_flags),
        .win_valid (f_valid), .win_id (f_win_id),
        .pkt_cnt (f_pkt), .byte_sum (f_bytes), .syn_cnt (f_syn),
        .src_ip_cnt (f_src), .dst_ip_cnt (f_dst), .dst_port_cnt (f_port), .err_cnt (f_err),
        .suspect_ip (f_susp), .confirm_cnt (f_conf)
    );

    // ---------------------------------------------------------------- Phan 3: bo loc + thanh ghi
    wire         bl_en, syn_lim_en;
    wire [15:0]  syn_limit;
    wire [7:0]   bl_valid;
    wire [255:0] bl_ip;
    wire         inc_fwd, inc_drop_bl, inc_drop_syn;

    wb_filter_regs u_filter_regs (
        .clk (clk), .rst (rst), .stb (stb_filter), .we (wb_we), .adr (wb_adr),
        .sel (wb_sel), .dat_w (wb_dat_w), .dat_r (dr_filter), .ack (ack_filter),
        .bl_en (bl_en), .syn_lim_en (syn_lim_en), .syn_limit (syn_limit),
        .bl_valid (bl_valid), .bl_ip (bl_ip),
        .inc_fwd (inc_fwd), .inc_drop_bl (inc_drop_bl), .inc_drop_syn (inc_drop_syn),
        .inc_crc_err (mac_crc_err), .inc_overflow (mac_overflow)
    );

    pkt_filter #(.SEC_CYCLES(SEC_CYCLES)) u_filter (
        .clk (clk), .rst_n (resetn),
        .bl_en (bl_en), .syn_lim_en (syn_lim_en), .syn_limit (syn_limit),
        .bl_valid (bl_valid), .bl_ip (bl_ip),
        .hdr_valid (h_valid), .hdr_dir (h_dir), .is_ipv4 (h_ipv4), .hdr_l4 (h_l4),
        .src_ip (h_src), .ip_proto (h_proto), .tcp_flags (h_flags),
        .verdict_valid (verdict_valid), .verdict_drop (verdict_drop),
        .inc_fwd (inc_fwd), .inc_drop_bl (inc_drop_bl), .inc_drop_syn (inc_drop_syn)
    );

    // ---------------------------------------------------------------- Phan 2: AI v6
    wire        a_start, a_busy, a_done;
    wire [47:0] a_feat, a_scores;
    wire [1:0]  a_class;

    wb_ai_regs u_ai_regs (
        .clk (clk), .rst (rst), .stb (stb_ai), .we (wb_we), .adr (wb_adr),
        .sel (wb_sel), .dat_w (wb_dat_w), .dat_r (dr_ai), .ack (ack_ai),
        .core_start (a_start), .core_feat (a_feat), .core_busy (a_busy),
        .core_done (a_done), .core_class (a_class), .core_scores (a_scores)
    );

    ai_core u_ai (
        .clk (clk), .rst_n (resetn), .start (a_start), .feat (a_feat),
        .busy (a_busy), .done (a_done), .class_id (a_class), .scores (a_scores)
    );

    // frm_crc_ok: khung CRC sai do Phan 4 tu xoa va dem (mac_crc_err); Phan 1 khong dung tin hieu nay
    wire unused_crc = frm_crc_ok;
endmodule
