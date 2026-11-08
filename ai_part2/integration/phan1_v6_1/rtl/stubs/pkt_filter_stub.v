// =============================================================================
// pkt_filter_stub.v - KHOI GIA cho Phan 3: quyet dinh cho qua / bo tung khung
//
// Moi ban ghi header (hdr_valid) -> dung 1 quyet dinh (verdict_valid) o chu ky ke tiep.
// Thu tu xet (chi chieu ngoai -> trong, chi goi IPv4; ARP va cac loai khac luon cho qua):
//   Lop 1 - danh sach chan: IP nguon trung 1 trong 8 o dang bat (bl_en = 1) -> bo
//   Lop 2 - gioi han SYN  : goi SYN mo ket noi CHUA bi lop 1 bo, vuot syn_limit goi trong
//           giay hien tai (syn_lim_en = 1) -> bo. Goi da bi lop 1 bo KHONG tinh vao suat SYN.
// Chieu trong -> ngoai luon cho qua.
// Xung dem (1 chu ky, cung luc verdict_valid): inc_fwd (khung ngoai->trong duoc cho qua),
// inc_drop_bl, inc_drop_syn -> dua vao wb_filter_regs.
//
// Cong giu theo tai lieu nhom; Phan 3 thay file nay bang pkt_filter.v that, GIU NGUYEN cong.
// =============================================================================
`timescale 1ns / 1ps
module pkt_filter #(
    parameter integer SEC_CYCLES = 27_000_000
) (
    input  wire         clk,
    input  wire         rst_n,
    // luat tu wb_filter_regs
    input  wire         bl_en,
    input  wire         syn_lim_en,
    input  wire [15:0]  syn_limit,
    input  wire [7:0]   bl_valid,
    input  wire [255:0] bl_ip,
    // ban ghi header
    input  wire         hdr_valid,
    input  wire         hdr_dir,
    input  wire         is_ipv4,
    input  wire         hdr_l4,
    input  wire [31:0]  src_ip,
    input  wire [7:0]   ip_proto,
    input  wire [7:0]   tcp_flags,
    // quyet dinh -> Phan 4
    output reg          verdict_valid,
    output reg          verdict_drop,
    // xung dem
    output reg          inc_fwd,
    output reg          inc_drop_bl,
    output reg          inc_drop_syn
);
    // ---- so sanh 8 o danh sach chan song song
    wire [7:0] eq;
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_cmp
            assign eq[g] = bl_valid[g] && (bl_ip[32*g +: 32] == src_ip);
        end
    endgenerate

    wire ingress  = !hdr_dir && is_ipv4;
    wire syn_open = (ip_proto == 8'd6) && hdr_l4 && tcp_flags[1] && !tcp_flags[4];
    wire hit_bl   = ingress && bl_en && (eq != 8'd0);

    // ---- dem SYN trong giay hien tai
    localparam integer CW = $clog2(SEC_CYCLES + 1);
    reg [CW-1:0] sec;
    reg [15:0]   syn_used;
    wire         over = syn_lim_en && (syn_used >= syn_limit);
    wire         hit_syn = ingress && !hit_bl && syn_open && over;

    always @(posedge clk) begin
        verdict_valid <= 1'b0;
        inc_fwd <= 1'b0; inc_drop_bl <= 1'b0; inc_drop_syn <= 1'b0;
        if (!rst_n) begin
            sec <= {CW{1'b0}};
            syn_used <= 16'd0;
            verdict_drop <= 1'b0;
        end else begin
            if (sec == SEC_CYCLES - 1) begin
                sec <= {CW{1'b0}};
                syn_used <= 16'd0;
            end else begin
                sec <= sec + 1'b1;
                if (hdr_valid && ingress && !hit_bl && syn_open && syn_used != 16'hFFFF)
                    syn_used <= syn_used + 16'd1;
            end
            if (hdr_valid) begin
                verdict_valid <= 1'b1;
                verdict_drop  <= hit_bl || hit_syn;
                inc_fwd       <= !hdr_dir && !(hit_bl || hit_syn);
                inc_drop_bl   <= hit_bl;
                inc_drop_syn  <= hit_syn;
            end
        end
    end
endmodule
