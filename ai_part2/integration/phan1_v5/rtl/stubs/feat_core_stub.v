// =============================================================================
// feat_core_stub.v - KHOI GIA cho Phan 3: thong ke dac trung theo cua so + IP nghi van
//
// Dac trung tinh DUNG dinh nghia AI v2 (Phan 2, spec/FEATURES_V0.md):
//   chi tinh goi chieu ngoai -> trong (hdr_dir = 0), IPv4 hop le, khong phan manh,
//   co IP dich thuoc mang bao ve ((dst & prot_mask) == (prot_net & prot_mask)).
//   pkt_cnt      so goi                       byte_sum  tong truong IPv4 Total Length
//   syn_cnt      so goi TCP SYN=1, ACK=0      src/dst/port: so gia tri KHAC NHAU, dem chinh xac
//   err_cnt      goi bi loai (phan manh) + goi mat do hang doi day
// Dem chinh xac toi TBL gia tri moi loai (128 >= nguong bao hoa 127 cua AI) bang bang tim tuan tu.
// Moc cua so: dem chu ky clock, WINDOW_CYCLES chu ky = 1 giay (cua so lien tiep, khong chong lan).
//
// IP nghi van (thuat toan da so Boyer-Moore tren cac goi SYN mo ket noi):
//   cua so n   : chon ung vien
//   cua so n+1 : dem so SYN tu dung ung vien do -> confirm_cnt; suspect_ip = ung vien cua so n
//
// Cong giu theo tai lieu nhom; Phan 3 thay file nay bang feat_core.v that, GIU NGUYEN cong.
// =============================================================================
`timescale 1ns / 1ps
module feat_core #(
    parameter integer WINDOW_CYCLES = 27_000_000,
    parameter integer TBL           = 128            // so o moi bang dem khac nhau
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire [31:0] prot_net,
    input  wire [31:0] prot_mask,
    // ban ghi header tu pkt_parser
    input  wire        hdr_valid,
    input  wire        hdr_dir,
    input  wire        is_ipv4,
    input  wire        hdr_frag,
    input  wire        hdr_l4,
    input  wire [31:0] src_ip,
    input  wire [31:0] dst_ip,
    input  wire [7:0]  ip_proto,
    input  wire [15:0] ip_len,
    input  wire [15:0] src_port,
    input  wire [15:0] dst_port,
    input  wire [7:0]  tcp_flags,
    // ket qua moi cua so: win_valid xung 1 chu ky, cac gia tri hop le cung chu ky do
    output reg         win_valid,
    output reg  [15:0] win_id,
    output reg  [31:0] pkt_cnt,
    output reg  [31:0] byte_sum,
    output reg  [31:0] syn_cnt,
    output reg  [15:0] src_ip_cnt,
    output reg  [15:0] dst_ip_cnt,
    output reg  [15:0] dst_port_cnt,
    output reg  [15:0] err_cnt,
    output reg  [31:0] suspect_ip,
    output reg  [31:0] confirm_cnt
);
    // ---------------------------------------------------------------- moc cua so
    localparam integer CW = $clog2(WINDOW_CYCLES + 1);
    reg [CW-1:0] tick;
    reg          win_tag;                 // dao moi khi het 1 cua so
    always @(posedge clk) begin
        if (!rst_n) begin
            tick <= {CW{1'b0}};
            win_tag <= 1'b0;
        end else if (!enable) begin
            tick <= {CW{1'b0}};
        end else if (tick == WINDOW_CYCLES - 1) begin
            tick <= {CW{1'b0}};
            win_tag <= ~win_tag;
        end else begin
            tick <= tick + 1'b1;
        end
    end

    // ---------------------------------------------------------------- hang doi ban ghi (8 o)
    // o = {tag, err, syn_open, l4, len[15:0], src[31:0], dst[31:0], dport[15:0]}
    localparam integer FW = 1 + 1 + 1 + 1 + 16 + 32 + 32 + 16;
    reg [FW-1:0] fq [0:7];
    reg [2:0]    fq_wr, fq_rd;
    reg [3:0]    fq_n;
    reg [15:0]   ovf_cnt;

    wire prot     = ((dst_ip & prot_mask) == (prot_net & prot_mask));
    wire accept   = hdr_valid && !hdr_dir && is_ipv4 && prot;
    wire syn_open = (ip_proto == 8'd6) && hdr_l4 && tcp_flags[1] && !tcp_flags[4];
    wire fq_full  = (fq_n == 4'd8);
    wire fq_empty = (fq_n == 4'd0);
    wire [FW-1:0] head = fq[fq_rd];
    wire          h_tag = head[FW-1];
    wire          h_err = head[FW-2];
    wire          h_syn = head[FW-3];
    wire          h_l4  = head[FW-4];
    wire [15:0]   h_len = head[FW-5 -: 16];
    wire [31:0]   h_src = head[79:48];
    wire [31:0]   h_dst = head[47:16];
    wire [15:0]   h_dpt = head[15:0];

    always @(posedge clk) begin
        if (accept && !fq_full)
            fq[fq_wr] <= {win_tag, hdr_frag, syn_open, hdr_l4, ip_len, src_ip, dst_ip, dst_port};
    end

    // ---------------------------------------------------------------- bang dem khac nhau
    reg [31:0] m_src  [0:TBL-1];
    reg [31:0] m_dst  [0:TBL-1];
    reg [15:0] m_port [0:TBL-1];
    reg [7:0]  n_src, n_dst, n_port;      // so o da dung trong cua so hien tai (0..TBL)
    reg [7:0]  k, kp, kmax;
    reg        cv;
    reg [31:0] rs, rd;
    reg [15:0] rp;
    reg        wr_s, wr_d, wr_p;

    always @(posedge clk) begin
        rs <= m_src[k[6:0]];
        rd <= m_dst[k[6:0]];
        rp <= m_port[k[6:0]];
        if (wr_s) m_src [n_src[6:0]]  <= e_src;
        if (wr_d) m_dst [n_dst[6:0]]  <= e_dst;
        if (wr_p) m_port[n_port[6:0]] <= e_port;
    end

    // ---------------------------------------------------------------- may trang thai
    localparam [1:0] S_IDLE = 2'd0, S_SEARCH = 2'd1, S_INSERT = 2'd2;
    reg [1:0]  st;
    reg        cur_tag;
    reg [31:0] e_src, e_dst;
    reg [15:0] e_port;
    reg        e_portv, hit_s, hit_d, hit_p;
    reg [31:0] a_pkt, a_bytes, a_syn, a_conf;
    reg [15:0] a_err;
    reg [31:0] bm_cand, bm_cnt, prev_cand;
    reg        prev_valid;

    wire finalize = (st == S_IDLE) && (cur_tag != win_tag) && (fq_empty || (h_tag != cur_tag));
    wire do_pop   = (st == S_IDLE) && !finalize && !fq_empty && (h_tag == cur_tag);

    always @(posedge clk) begin
        win_valid <= 1'b0;
        wr_s <= 1'b0; wr_d <= 1'b0; wr_p <= 1'b0;
        if (!rst_n) begin
            st <= S_IDLE; cur_tag <= 1'b0;
            fq_wr <= 3'd0; fq_rd <= 3'd0; fq_n <= 4'd0; ovf_cnt <= 16'd0;
            n_src <= 8'd0; n_dst <= 8'd0; n_port <= 8'd0;
            k <= 8'd0; kp <= 8'd0; kmax <= 8'd0; cv <= 1'b0;
            a_pkt <= 32'd0; a_bytes <= 32'd0; a_syn <= 32'd0; a_conf <= 32'd0; a_err <= 16'd0;
            bm_cand <= 32'd0; bm_cnt <= 32'd0; prev_cand <= 32'd0; prev_valid <= 1'b0;
            win_id <= 16'd0;
            pkt_cnt <= 32'd0; byte_sum <= 32'd0; syn_cnt <= 32'd0;
            src_ip_cnt <= 16'd0; dst_ip_cnt <= 16'd0; dst_port_cnt <= 16'd0; err_cnt <= 16'd0;
            suspect_ip <= 32'd0; confirm_cnt <= 32'd0;
        end else begin
            // ---- hang doi: ghi / doc
            if (accept && fq_full && ovf_cnt != 16'hFFFF) ovf_cnt <= ovf_cnt + 16'd1;
            if (accept && !fq_full) fq_wr <= fq_wr + 3'd1;
            if (do_pop) fq_rd <= fq_rd + 3'd1;
            fq_n <= fq_n + ((accept && !fq_full) ? 4'd1 : 4'd0) - (do_pop ? 4'd1 : 4'd0);

            case (st)
                S_IDLE: begin
                    if (finalize) begin
                        // ---- chot cua so
                        win_valid    <= 1'b1;
                        pkt_cnt      <= a_pkt;
                        byte_sum     <= a_bytes;
                        syn_cnt      <= a_syn;
                        src_ip_cnt   <= {8'd0, n_src};
                        dst_ip_cnt   <= {8'd0, n_dst};
                        dst_port_cnt <= {8'd0, n_port};
                        err_cnt      <= a_err + ovf_cnt;
                        suspect_ip   <= prev_valid ? prev_cand : 32'd0;
                        confirm_cnt  <= a_conf;
                        // ---- cua so moi
                        prev_cand  <= bm_cand;
                        prev_valid <= (bm_cnt != 32'd0);
                        bm_cnt <= 32'd0;
                        a_pkt <= 32'd0; a_bytes <= 32'd0; a_syn <= 32'd0; a_conf <= 32'd0;
                        a_err <= 16'd0; ovf_cnt <= 16'd0;
                        n_src <= 8'd0; n_dst <= 8'd0; n_port <= 8'd0;
                        cur_tag <= ~cur_tag;
                    end else if (do_pop) begin
                        if (h_err) begin
                            if (a_err != 16'hFFFF) a_err <= a_err + 16'd1;
                        end else begin
                            a_pkt   <= a_pkt + 32'd1;
                            a_bytes <= a_bytes + {16'd0, h_len};
                            if (h_syn) begin
                                a_syn <= a_syn + 32'd1;
                                if (prev_valid && h_src == prev_cand) a_conf <= a_conf + 32'd1;
                                if (bm_cnt == 32'd0) begin
                                    bm_cand <= h_src; bm_cnt <= 32'd1;
                                end else if (h_src == bm_cand) begin
                                    bm_cnt <= bm_cnt + 32'd1;
                                end else begin
                                    bm_cnt <= bm_cnt - 32'd1;
                                end
                            end
                            e_src <= h_src; e_dst <= h_dst; e_port <= h_dpt; e_portv <= h_l4;
                            hit_s <= 1'b0; hit_d <= 1'b0; hit_p <= 1'b0;
                            k <= 8'd0; cv <= 1'b0;
                            kmax <= (n_src > n_dst) ? ((h_l4 && n_port > n_src) ? n_port : n_src)
                                                    : ((h_l4 && n_port > n_dst) ? n_port : n_dst);
                            st <= S_SEARCH;
                        end
                    end
                end
                S_SEARCH: begin
                    // so sanh o kp (du lieu doc o chu ky truoc)
                    if (cv) begin
                        if (kp < n_src  && rs == e_src)             hit_s <= 1'b1;
                        if (kp < n_dst  && rd == e_dst)             hit_d <= 1'b1;
                        if (kp < n_port && rp == e_port && e_portv) hit_p <= 1'b1;
                    end
                    if (k < kmax) begin
                        kp <= k; cv <= 1'b1; k <= k + 8'd1;
                    end else begin
                        cv <= 1'b0;
                        if (!cv) st <= S_INSERT;
                    end
                end
                S_INSERT: begin
                    if (!hit_s && n_src < TBL) begin wr_s <= 1'b1; end
                    if (!hit_d && n_dst < TBL) begin wr_d <= 1'b1; end
                    if (e_portv && !hit_p && n_port < TBL) begin wr_p <= 1'b1; end
                    st <= 2'd3;
                end
                default: begin            // tang so o sau khi da ghi (dia chi ghi = n cu)
                    if (wr_s) n_src  <= n_src  + 8'd1;
                    if (wr_d) n_dst  <= n_dst  + 8'd1;
                    if (wr_p) n_port <= n_port + 8'd1;
                    st <= S_IDLE;
                end
            endcase
            if (win_valid) win_id <= win_id + 16'd1;
        end
    end
endmodule
