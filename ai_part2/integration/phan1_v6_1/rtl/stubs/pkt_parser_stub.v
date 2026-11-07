// =============================================================================
// pkt_parser_stub.v - KHOI GIA cho Phan 3: tach header tu dong byte cua khung Ethernet
//
// Vao : dong byte frm_* tu Phan 4 (mien clock he thong, da bo preamble, gom ca 4 byte CRC)
// Ra  : 1 ban ghi header cho MOI khung (hdr_valid xung 1 chu ky), truoc frm_eof khi khung du dai,
//       hoac ngay sau byte cuoi neu khung bi cat ngan.
//
// Ho tro: Ethernet II khong VLAN, IPv4 co/khong co option (IHL >= 5), TCP, UDP.
//   is_ipv4  = 1: EtherType 0x0800, version 4, IHL >= 5, nhan du toi het IP dich
//   hdr_frag = 1: goi IPv4 la phan manh (MF = 1 hoac offset != 0) -> khong dua vao thong ke
//   hdr_l4   = 1: TCP/UDP, khong phan manh, nhan du cong (va co TCP) -> src_port/dst_port/tcp_flags hop le
// Truong 2 bit hdr_frag/hdr_l4 la phan BO SUNG so voi bang giao tiep ban dau - xem bao cao ghep.
//
// Khi Phan 3 xong: thay file nay bang pkt_parser.v that, GIU NGUYEN ten module va cac cong.
// =============================================================================
`timescale 1ns / 1ps
module pkt_parser (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        frm_valid,
    input  wire [7:0]  frm_data,
    input  wire        frm_sof,
    input  wire        frm_eof,
    input  wire        frm_dir,
    output reg         hdr_valid,
    output reg         hdr_dir,
    output reg         is_ipv4,
    output reg         hdr_frag,
    output reg         hdr_l4,
    output reg  [31:0] src_ip,
    output reg  [31:0] dst_ip,
    output reg  [7:0]  ip_proto,
    output reg  [15:0] ip_len,
    output reg  [15:0] src_port,
    output reg  [15:0] dst_port,
    output reg  [7:0]  tcp_flags
);
    reg [10:0] idx;          // so thu tu byte tiep theo
    reg [10:0] got;          // so byte da nhan cua khung hien tai
    reg [10:0] need;         // can bao nhieu byte de du header
    reg        emitted, emit_now;

    reg        w_dir;
    reg [15:0] w_et;
    reg [7:0]  w_vihl;
    reg [15:0] w_len, w_frag;
    reg [7:0]  w_proto, w_flags;
    reg [31:0] w_src, w_dst;
    reg [15:0] w_sport, w_dport;

    wire [10:0] i   = frm_sof ? 11'd0 : idx;
    wire [10:0] l4s = 11'd14 + {5'd0, w_vihl[3:0], 2'b00};     // dau header L4 (sau byte 14)

    always @(posedge clk) begin
        hdr_valid <= 1'b0;
        if (!rst_n) begin
            idx <= 11'd0; got <= 11'd0; need <= 11'h7FF;
            emitted <= 1'b1; emit_now <= 1'b0;
        end else begin
            // ---- xuat ban ghi (tu gia tri da chot o chu ky truoc)
            if (emit_now) begin
                hdr_valid <= 1'b1;
                hdr_dir   <= w_dir;
                is_ipv4   <= (w_et == 16'h0800) && (w_vihl[7:4] == 4'd4) &&
                             (w_vihl[3:0] >= 4'd5) && (got >= 11'd34);
                hdr_frag  <= w_frag[13] || (w_frag[12:0] != 13'd0);
                hdr_l4    <= (w_et == 16'h0800) && (w_vihl[7:4] == 4'd4) && (w_vihl[3:0] >= 4'd5) &&
                             !(w_frag[13] || (w_frag[12:0] != 13'd0)) &&
                             ((w_proto == 8'd6) || (w_proto == 8'd17)) && (got >= need);
                src_ip    <= w_src;
                dst_ip    <= w_dst;
                ip_proto  <= w_proto;
                ip_len    <= w_len;
                src_port  <= w_sport;
                dst_port  <= w_dport;
                tcp_flags <= (w_proto == 8'd6) ? w_flags : 8'd0;
            end
            emit_now <= 1'b0;

            if (frm_valid) begin
                if (frm_sof) begin
                    w_dir <= frm_dir;
                    w_et <= 16'd0; w_vihl <= 8'd0; w_len <= 16'd0; w_frag <= 16'd0;
                    w_proto <= 8'd0; w_flags <= 8'd0; w_src <= 32'd0; w_dst <= 32'd0;
                    w_sport <= 16'd0; w_dport <= 16'd0;
                    need <= 11'h7FF;
                    emitted <= 1'b0;
                end
                idx <= i + 11'd1;
                got <= i + 11'd1;

                case (i)
                    11'd12: w_et[15:8]   <= frm_data;
                    11'd13: begin
                        w_et[7:0] <= frm_data;
                        if ({w_et[15:8], frm_data} != 16'h0800) need <= 11'd14;
                    end
                    11'd14: w_vihl       <= frm_data;
                    11'd16: w_len[15:8]  <= frm_data;
                    11'd17: w_len[7:0]   <= frm_data;
                    11'd20: w_frag[15:8] <= frm_data;
                    11'd21: w_frag[7:0]  <= frm_data;
                    11'd23: begin
                        w_proto <= frm_data;
                        if (w_vihl[7:4] != 4'd4 || w_vihl[3:0] < 4'd5) need <= 11'd34;
                        else if (frm_data == 8'd6)  need <= l4s + 11'd14;
                        else if (frm_data == 8'd17) need <= l4s + 11'd4;
                        else                        need <= 11'd34;
                    end
                    11'd26: w_src[31:24] <= frm_data;
                    11'd27: w_src[23:16] <= frm_data;
                    11'd28: w_src[15: 8] <= frm_data;
                    11'd29: w_src[ 7: 0] <= frm_data;
                    11'd30: w_dst[31:24] <= frm_data;
                    11'd31: w_dst[23:16] <= frm_data;
                    11'd32: w_dst[15: 8] <= frm_data;
                    11'd33: w_dst[ 7: 0] <= frm_data;
                    default: ;
                endcase
                if (i >= 11'd34) begin
                    if (i == l4s)            w_sport[15:8] <= frm_data;
                    if (i == l4s + 11'd1)    w_sport[7:0]  <= frm_data;
                    if (i == l4s + 11'd2)    w_dport[15:8] <= frm_data;
                    if (i == l4s + 11'd3)    w_dport[7:0]  <= frm_data;
                    if (i == l4s + 11'd13)   w_flags       <= frm_data;
                end

                // du header (byte cuoi can thiet vua vao) hoac het khung -> xuat o chu ky sau
                if (!(emitted && !frm_sof) &&
                    ((i + 11'd1 == ((i == 11'd13 && {w_et[15:8], frm_data} != 16'h0800) ? 11'd14 : need)) || frm_eof)) begin
                    emit_now <= 1'b1;
                    emitted  <= 1'b1;
                end
            end
        end
    end
endmodule
