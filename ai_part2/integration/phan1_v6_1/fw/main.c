/* =============================================================================
 * main.c - Firmware tuong lua Ethernet (Phan 1) - PicoRV32 RV32I, AI v6 cua Phan 2
 *
 * Khoi dong:
 *   - Tu kiem tra (POST): bus, thanh ghi, 37 vector tich hop cua Phan 2 (ca phan mem
 *     ai_v6_prepare_window() lan AI phan cung qua bus), man OLED.
 *   - Dat mang can bao ve (PROT_NET/PROT_MASK), che do luc khoi dong, lop 2 (tat).
 * Vong lap chinh:
 *   - Moi cua so (1 s): doc dac trung -> AI -> cong kiem tra hop ly -> dem cua so lien
 *     tiep -> xac nhan IP nghi van -> danh sach trang -> chan / gia han (chi o che do CHAN).
 *     Luat nguong cua Phan 2 chay song song, chi ghi log de so sanh.
 *   - Moi giay (dem bang SYS_CYCLE): giam han, tu go o het han, in bo dem goi, cap nhat OLED.
 *   - Nut S1: nhan ngan = doi CHI PHAT HIEN <-> CHAN; nhan giu >= 2 s = bat/tat lop 2.
 *   - Luc ranh: ve 1 dong OLED co thay doi.
 *
 * Log qua USB-UART (115200 8N1, moi dong ket thuc CR LF; CS = XOR cac ky tu giua '$' va '*',
 * 2 so hex; dong bat dau '#' la ghi chu, chuong trinh doc log bo qua):
 *   $IDS,win,cls,alert,pkt,avg,syn,src,dst,port,flags,lat,base,s0,s1,s2,susp,conf*CS
 *       11 truong dau GIU NGUYEN nhu ban cu:
 *       win   so thu tu cua so         cls   lop AI tho: 0 BT, 1 DoS (SYN flood), 2 quet cong
 *       alert ket luan sau cong kiem tra + 2 cua so lien tiep (0/1/2)
 *       pkt   so goi    avg  byte/goi  syn  % goi SYN mo ket noi (0..100)
 *       src/dst/port  so IP nguon / IP dich / cong dich khac nhau
 *       flags bit0 mat cua so (OVERRUN)   bit1 AI qua thoi gian  bit2 co goi bi loai khoi thong ke
 *             bit3 cua so rong, khong goi AI    bit4 cong kiem tra hop ly da doi ket qua AI
 *             bit5 IP nghi van thuoc danh sach trang   bit6 IP nghi van khong chiem qua nua SYN
 *             bit7 danh sach chan day, da thay o cu nhat
 *       lat   so chu ky AI (0 neu khong goi AI)
 *       6 truong them: base lop cua luat nguong, s0..s2 diem AI (int16), susp IP nghi van,
 *       conf so SYN tu IP nghi van trong cua so nay
 *   $BLK,ip,DOS|SCAN,han_giay   $UNB,ip   $CNT,fwd,drop_bl,drop_syn,crc_err,overflow (moi giay)
 *   $MODE,DETECT|BLOCK          $SYN,ON,gioi_han | $SYN,OFF
 * ========================================================================== */
#include <stdint.h>
#include "hw.h"
#include "config.h"
#include "uart.h"
#include "oled.h"
#include "part2/ai_v6_integration.h"
#include "ai_vectors.h"

/* ---------------------------------------------------------------- flags $IDS */
#define F_OVERRUN   (1u << 0)
#define F_AI_TMO    (1u << 1)
#define F_ERR       (1u << 2)
#define F_EMPTY     (1u << 3)
#define F_GATE      (1u << 4)
#define F_ALLOW     (1u << 5)
#define F_NOCONF    (1u << 6)
#define F_BL_FULL   (1u << 7)

enum { CLS_NORMAL = 0, CLS_DOS = 1, CLS_SCAN = 2 };
static const char *const cls_log[3]  = { "BT", "DOS", "SCAN" };
static const char *const cls_oled[3] = { "BT", "DoS", "SCAN" };

typedef struct {
    uint32_t win, pkt, bytes, syn, src, dst, port, err, susp, conf;
} win_t;

typedef struct {
    uint32_t ip;
    uint32_t ttl;           /* giay con lai, 0 = o trong */
    uint32_t reason;
} slot_t;

static const uint32_t allow_list[] = ALLOW_LIST;
#define ALLOW_N ((int)(sizeof(allow_list) / sizeof(allow_list[0])))

static slot_t   bl[FLT_BL_SLOTS];
static uint32_t bl_mask;            /* ban sao cua FLT_BL_VALID */
static uint32_t mode;               /* 0 = chi phat hien, 1 = chan */
static uint32_t syn_en;
static uint32_t sec_cycles;
static uint32_t streak;
static uint32_t last_lat;
static uint32_t post_err;

/* gia tri hien tren OLED */
static uint32_t o_win, o_ai, o_base, o_dec, o_alert, o_empty;
static uint32_t o_fwd, o_drop;

/* ================================================================ log */
static char     lb[160];
static strbuf_t sb;

static void msg_begin(const char *tag) { sb_init(&sb, lb, sizeof(lb)); sb_puts(&sb, tag); }
static void msg_c(void)                { sb_putc(&sb, ','); }
static void msg_u(uint32_t v)          { sb_putc(&sb, ','); sb_u32(&sb, v); }
static void msg_s(const char *s)       { sb_putc(&sb, ','); sb_puts(&sb, s); }
static void sb_i32(strbuf_t *b, int32_t v)
{
    if (v < 0) { sb_putc(b, '-'); sb_u32(b, (uint32_t)(-v)); }
    else       sb_u32(b, (uint32_t)v);
}
static void sb_ip(strbuf_t *b, uint32_t ip)
{
    for (int i = 3; i >= 0; i--) {
        sb_u32(b, (ip >> (8 * i)) & 0xFFu);
        if (i) sb_putc(b, '.');
    }
}
static void msg_ip(uint32_t ip)        { sb_putc(&sb, ','); sb_ip(&sb, ip); }

static void msg_end(void)              /* them *CS\r\n roi gui */
{
    uint8_t cs = 0;
    for (uint32_t i = 1; i < sb.len; i++)
        cs ^= (uint8_t)lb[i];
    sb_putc(&sb, '*');
    sb_hex(&sb, cs, 2);
    sb_puts(&sb, "\r\n");
    uart_puts(lb);
}

static void note(const char *s)        /* dong ghi chu */
{
    uart_puts("# ");
    uart_puts(s);
    uart_puts("\r\n");
}

/* ================================================================ AI */
/* Chay 1 lan suy luan. Tra ve lop (0..2) hoac -1 neu qua thoi gian. */
static int ai_run(uint32_t lo, uint32_t hi, int32_t sc[3], uint32_t *lat)
{
    AI_FEAT_LO = lo;
    AI_FEAT_HI = hi;
    AI_CTRL = AI_CTRL_START;
    uint32_t t0 = SYS_CYCLE;
    while (!(AI_STATUS & AI_ST_DONE)) {
        if (SYS_CYCLE - t0 > AI_TIMEOUT_CYC) {
            AI_CTRL = AI_CTRL_ABORT;
            return -1;
        }
    }
    sc[0] = (int32_t)AI_SCORE0;
    sc[1] = (int32_t)AI_SCORE1;
    sc[2] = (int32_t)AI_SCORE2;
    *lat  = AI_LAT;
    return (int)(AI_RESULT & 3u);
}

/* Luat nguong cua Phan 2 (chi de so sanh, khong dung de chan) */
static int baseline(const win_t *w)
{
    if (!w->pkt) return CLS_NORMAL;
    uint32_t synq = (127u * w->syn) / w->pkt;
    if (w->port >= 3 && synq >= 32) return CLS_SCAN;
    if (w->pkt >= 24 && synq >= 32) return CLS_DOS;
    return CLS_NORMAL;
}

/* ================================================================ POST */
static uint32_t post(void)
{
    uint32_t err = 0;
    if (SYS_ID != SYS_ID_VALUE) err |= 1u << 0;
    SYS_SCRATCH = 0xA5C3965Au;
    if (SYS_SCRATCH != 0xA5C3965Au) err |= 1u << 1;
    SYS_SCRATCH = 0;

    /* thanh ghi bo loc */
    FLT_SYN_LIMIT = 0x1234u;
    if (FLT_SYN_LIMIT != 0x1234u) err |= 1u << 2;
    if (FLT_BL_VALID != 0u)       err |= 1u << 2;

    /* 37 vector tich hop cua Phan 2 */
    int bad = 0;
    for (int i = 0; i < AI_VEC_N; i++) {
        const ai_vec_t *v = &ai_vec[i];
        uint64_t feat;
        int valid = ai_v6_prepare_window(v->cnt[0], v->cnt[1], v->cnt[2],
                                         v->cnt[3], v->cnt[4], v->cnt[5], &feat);
        if ((uint32_t)valid != v->valid ||
            (uint32_t)feat != v->feat_lo || (uint32_t)(feat >> 32) != v->feat_hi) {
            bad++;
            msg_begin("# POST vector "); sb_u32(&sb, (uint32_t)i);
            sb_puts(&sb, ": dong goi dac trung sai"); sb_puts(&sb, "\r\n"); uart_puts(lb);
        }
        /* Empty window checks the CPU guard only: no accelerator START. */
        if (!v->valid) continue;
        int32_t sc[3];
        uint32_t lat = 0;
        int c = ai_run(v->feat_lo, v->feat_hi, sc, &lat);
        if (c != (int)v->cls || sc[0] != v->score[0] || sc[1] != v->score[1] ||
            sc[2] != v->score[2]) {
            bad++;
            msg_begin("# POST vector "); sb_u32(&sb, (uint32_t)i);
            sb_puts(&sb, ": AI tra "); sb_i32(&sb, c);
            sb_puts(&sb, " ("); sb_i32(&sb, sc[0]); sb_putc(&sb, ' ');
            sb_i32(&sb, sc[1]); sb_putc(&sb, ' '); sb_i32(&sb, sc[2]);
            sb_puts(&sb, ") can "); sb_u32(&sb, v->cls); sb_puts(&sb, "\r\n"); uart_puts(lb);
        }
        last_lat = lat;
    }
    if (bad) err |= 1u << 3;
    return err;
}

/* ================================================================ danh sach chan */
static void hw_bl_apply(void)
{
    FLT_BL_VALID = bl_mask;
}

static void unblock(int i)
{
    bl_mask &= ~(1u << i);
    hw_bl_apply();                       /* tat o truoc, roi moi xoa IP */
    FLT_BL_IP(i) = 0;
    msg_begin("$UNB"); msg_ip(bl[i].ip); msg_end();
    bl[i].ttl = 0;
    bl[i].ip  = 0;
}

static int bl_find(uint32_t ip)
{
    for (int i = 0; i < FLT_BL_SLOTS; i++)
        if (bl[i].ttl && bl[i].ip == ip) return i;
    return -1;
}

static int bl_count(void)
{
    int n = 0;
    for (int i = 0; i < FLT_BL_SLOTS; i++)
        if (bl[i].ttl) n++;
    return n;
}

static void block(uint32_t ip, uint32_t reason, uint32_t *flags)
{
    int i = bl_find(ip);
    if (i >= 0) {                        /* dang chan: gia han */
        bl[i].ttl = BLOCK_TTL_S;
        return;
    }
    for (i = 0; i < FLT_BL_SLOTS && bl[i].ttl; i++)
        ;
    if (i == FLT_BL_SLOTS) {             /* day: thay o sap het han nhat */
        int k = 0;
        for (int j = 1; j < FLT_BL_SLOTS; j++)
            if (bl[j].ttl < bl[k].ttl) k = j;
        unblock(k);
        i = k;
        *flags |= F_BL_FULL;
    }
    FLT_BL_IP(i) = ip;                   /* ghi IP truoc, bat o sau */
    bl_mask |= 1u << i;
    hw_bl_apply();
    bl[i].ip = ip;
    bl[i].ttl = BLOCK_TTL_S;
    bl[i].reason = reason;
    msg_begin("$BLK"); msg_ip(ip); msg_s(cls_log[reason]); msg_u(BLOCK_TTL_S); msg_end();
}

static int allowed(uint32_t ip)
{
    for (int i = 0; i < ALLOW_N; i++)
        if (allow_list[i] == ip) return 1;
    return 0;
}

/* ================================================================ che do */
static void filter_ctrl(void)
{
    FLT_CTRL = (mode ? FLT_CTRL_BL_EN : 0u) | (syn_en ? FLT_CTRL_SYN_EN : 0u);
}

static void set_mode(uint32_t m)
{
    mode = m;
    if (!mode)                           /* chi phat hien: go het IP dang chan */
        for (int i = 0; i < FLT_BL_SLOTS; i++)
            if (bl[i].ttl) unblock(i);
    filter_ctrl();
    msg_begin("$MODE"); msg_s(mode ? "BLOCK" : "DETECT"); msg_end();
}

static void set_syn(uint32_t on)
{
    syn_en = on;
    FLT_SYN_LIMIT = SYN_LIMIT_PER_S;
    filter_ctrl();
    msg_begin("$SYN");
    if (on) { msg_s("ON"); msg_u(SYN_LIMIT_PER_S); }
    else    msg_s("OFF");
    msg_end();
}

/* ================================================================ OLED */
static void line_kv(int line, const char *k, uint32_t v, const char *unit)
{
    char b[24];
    strbuf_t s;
    sb_init(&s, b, sizeof(b));
    sb_puts(&s, k); sb_u32(&s, v); sb_puts(&s, unit);
    oled_set_line(line, b);
}

static void oled_update(void)
{
    char b[24];
    strbuf_t s;
    if (!oled_ok())                      /* khong co man: khong ton thoi gian dinh dang */
        return;

    /* dong 0: ten + che do (+ dau hieu lop 2) */
    oled_set_line(0, mode ? (syn_en ? "IDS GW SYN    [CHAN]" : "IDS GW        [CHAN]")
                          : (syn_en ? "IDS GW SYN[PHAT HIEN]" : "IDS GW   [PHAT HIEN]"));
    /* dong 1: ket luan cua so gan nhat */
    sb_init(&s, b, sizeof(b));
    sb_puts(&s, "Cua so "); sb_u32(&s, o_win % 1000u); sb_puts(&s, ": ");
    if (o_empty)       sb_puts(&s, "rong");
    else if (o_alert)  { sb_puts(&s, cls_oled[o_alert]); sb_putc(&s, '!'); }
    else if (o_dec)    { sb_puts(&s, "nghi "); sb_puts(&s, cls_oled[o_dec]); }
    else               sb_puts(&s, "BT");
    oled_set_line(1, post_err ? "POST LOI - xem log" : b);
    /* dong 2: AI tho va luat nguong */
    sb_init(&s, b, sizeof(b));
    sb_puts(&s, "AI:"); sb_puts(&s, o_empty ? "-" : cls_oled[o_ai]);
    sb_puts(&s, "  Luat:"); sb_puts(&s, cls_oled[o_base]);
    oled_set_line(2, b);
    /* dong 3, 4: goi qua / bo trong giay vua roi */
    line_kv(3, "Qua : ", o_fwd, " goi/s");
    line_kv(4, "Bo  : ", o_drop, " goi/s");
    /* dong 5, 6: IP dang chan (o con lau nhat) */
    int n = bl_count(), k = -1;
    for (int i = 0; i < FLT_BL_SLOTS; i++)
        if (bl[i].ttl && (k < 0 || bl[i].ttl > bl[k].ttl)) k = i;
    sb_init(&s, b, sizeof(b));
    sb_puts(&s, "Chan: ");
    if (k < 0) sb_puts(&s, mode ? "-" : "(tat)");
    else       sb_ip(&s, bl[k].ip);
    oled_set_line(5, b);
    sb_init(&s, b, sizeof(b));
    if (k >= 0) {
        sb_puts(&s, "      con "); sb_u32(&s, bl[k].ttl); sb_puts(&s, " s");
        if (n > 1) { sb_puts(&s, " ("); sb_u32(&s, (uint32_t)n); sb_puts(&s, " IP)"); }
    }
    oled_set_line(6, b);
    /* dong 7: do tre AI */
    line_kv(7, "AI  : ", last_lat, " chu ky");
}

/* ================================================================ moi cua so */
static void process_window(void)
{
    win_t w;
    uint32_t flags = 0;
    uint32_t st = FEAT_STATUS;
    w.win   = FEAT_WIN_ID;
    w.pkt   = FEAT_PKT_CNT;
    w.bytes = FEAT_BYTE_SUM;
    w.syn   = FEAT_SYN_CNT;
    w.src   = FEAT_SRC_IP;
    w.dst   = FEAT_DST_IP;
    w.port  = FEAT_DST_PORT;
    w.err   = FEAT_ERR_CNT;
    w.susp  = FEAT_SUSPECT_IP;
    w.conf  = FEAT_CONFIRM_CNT;
    FEAT_CTRL = FEAT_CTRL_ENABLE | FEAT_CTRL_ACK | FEAT_CTRL_CLR_OVR;
    if (st & FEAT_ST_OVERRUN) flags |= F_OVERRUN;
    if (w.err)                flags |= F_ERR;

    /* 1. AI: skip only raw packet_count=0; q0=0 is valid for 1..7 packets. */
    uint64_t feat;
    int32_t  sc[3] = { 0, 0, 0 };
    uint32_t lat = 0;
    int cls = CLS_NORMAL;
    if (!ai_v6_prepare_window(w.pkt, w.bytes, w.syn, w.src, w.dst, w.port, &feat)) {
        flags |= F_EMPTY;
    } else {
        cls = ai_run((uint32_t)feat, (uint32_t)(feat >> 32), sc, &lat);
        if (cls < 0) { cls = CLS_NORMAL; flags |= F_AI_TMO; }
        else         last_lat = lat;
    }

    /* 2. cong kiem tra hop ly */
    int dec = cls;
    if (SCAN_MIN_PORTS && dec == CLS_SCAN && w.port < SCAN_MIN_PORTS) { dec = CLS_NORMAL; flags |= F_GATE; }
    if (DOS_MIN_SYN && dec == CLS_DOS && w.syn < DOS_MIN_SYN)         { dec = CLS_NORMAL; flags |= F_GATE; }

    /* 3. tan cong >= ALERT_ON_N cua so lien tiep */
    if (dec == CLS_NORMAL)      streak = 0;
    else if (streak < 255u)     streak++;
    int alert = (streak >= ALERT_ON_N) ? dec : CLS_NORMAL;

    /* 4. xac nhan IP nghi van + danh sach trang -> chan */
    if (alert) {
        int confirmed = (w.susp != 0) && (2u * w.conf > w.syn);
        if (!confirmed)            flags |= F_NOCONF;
        else if (allowed(w.susp))  flags |= F_ALLOW;
        else if (mode)             block(w.susp, (uint32_t)alert, &flags);
    }

    int base = baseline(&w);
    uint32_t avg = w.pkt ? w.bytes / w.pkt : 0;
    uint32_t synp = w.pkt ? (100u * w.syn) / w.pkt : 0;

    msg_begin("$IDS");
    msg_u(w.win); msg_u((uint32_t)cls); msg_u((uint32_t)alert);
    msg_u(w.pkt); msg_u(avg); msg_u(synp);
    msg_u(w.src); msg_u(w.dst); msg_u(w.port); msg_u(flags); msg_u(lat);
    msg_u((uint32_t)base);
    msg_c(); sb_i32(&sb, sc[0]); msg_c(); sb_i32(&sb, sc[1]); msg_c(); sb_i32(&sb, sc[2]);
    msg_ip(w.susp); msg_u(w.conf);
    msg_end();

    o_win = w.win; o_ai = (uint32_t)cls; o_base = (uint32_t)base;
    o_dec = (uint32_t)dec; o_alert = (uint32_t)alert; o_empty = (flags & F_EMPTY) != 0;
    /* man OLED cap nhat o per_second() */
}

/* ================================================================ moi giay */
static uint32_t c_prev[5];
static uint32_t sec_no;
static int      ref_ok[2] = { -1, -1 };

static void per_second(void)
{
    sec_no++;
    /* 1. han chan */
    for (int i = 0; i < FLT_BL_SLOTS; i++)
        if (bl[i].ttl && --bl[i].ttl == 0)
            unblock(i);
    /* 2. bo dem goi: hieu so voi giay truoc (khong xoa bo dem phan cung) */
    uint32_t c[5] = { FLT_CNT_FWD, FLT_CNT_DROP_BL, FLT_CNT_DROP_SYN,
                      FLT_CNT_CRC_ERR, FLT_CNT_OVERFLOW };
    msg_begin("$CNT");
    for (int i = 0; i < 5; i++) {
        uint32_t d = c[i] - c_prev[i];
        c_prev[i] = c[i];
        msg_u(d);
        if (i == 0) o_fwd = d;
        if (i == 1) o_drop = d;
        if (i == 2) o_drop += d;
    }
    msg_end();
    /* 3. tan so REF_CLK cua 2 module LAN8720 (in khi doi trang thai).
     *    clk_meter dem so canh trong 1 "giay" = SEC_CYCLES chu ky 27 MHz, nen gia tri dung
     *    la SEC_CYCLES * 50/27 (= 50 000 000 tren kit; nho hon khi mo phong), sai so 2%. */
    if (sec_no >= 2) {
        uint32_t exp = (sec_cycles / 27u) * 50u, tol = exp / 50u;
        uint32_t a = SYS_REFA_HZ, b = SYS_REFB_HZ;
        int oka = a > exp - tol && a < exp + tol;
        int okb = b > exp - tol && b < exp + tol;
        if (oka != ref_ok[0] || okb != ref_ok[1]) {
            ref_ok[0] = oka; ref_ok[1] = okb;
            msg_begin("# REF_CLK A="); sb_u32(&sb, a); sb_puts(&sb, oka ? " OK" : " LOI");
            sb_puts(&sb, ", B="); sb_u32(&sb, b); sb_puts(&sb, okb ? " OK" : " LOI");
            sb_puts(&sb, " (can ~"); sb_u32(&sb, exp);
            sb_puts(&sb, "; 0 = chua noi LAN8720 hoac dut day REF_CLK)\r\n");
            uart_puts(lb);
        }
    }
    oled_update();
}

/* ================================================================ nut S1 */
static uint32_t btn_prev, btn_t0, btn_long_done;

static void button(void)
{
    uint32_t now = SYS_CYCLE;
    uint32_t b = SYS_BTN & 1u;
    uint32_t long_cyc = (sec_cycles / 1000u) * LONG_PRESS_MS;
    if (b && !btn_prev) {
        btn_t0 = now;
        btn_long_done = 0;
    } else if (b && !btn_long_done && now - btn_t0 >= long_cyc) {
        btn_long_done = 1;               /* nhan giu: bat/tat lop 2 */
        set_syn(!syn_en);
        oled_update();
    } else if (!b && btn_prev && !btn_long_done) {
        if (now - btn_t0 >= long_cyc)    /* da nha nhung giu du lau (vong lap ban, chua kip thay) */
            set_syn(!syn_en);
        else
            set_mode(!mode);             /* nhan ngan: doi che do */
        oled_update();
    }
    btn_prev = b;
}

/* ================================================================ main */
int main(void)
{
    note("IDS GW - tuong lua Ethernet, PicoRV32 RV32I, AI v6 6-8-3 (Phan 2)");
    note("AI V6 SHA256 3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515");
    sec_cycles = SYS_SEC_CYCLES;

    uint32_t perr = post();
    post_err = perr;
    int has_oled = oled_init();
    msg_begin("# POST ");
    if (perr == 0) { sb_puts(&sb, "OK: bus, thanh ghi, AI "); sb_u32(&sb, AI_VEC_N);
                     sb_puts(&sb, "/"); sb_u32(&sb, AI_VEC_N); sb_puts(&sb, " vector, LAT ");
                     sb_u32(&sb, last_lat); sb_puts(&sb, " chu ky"); }
    else           { sb_puts(&sb, "LOI 0x"); sb_hex(&sb, perr, 2); }
    sb_puts(&sb, has_oled ? ", OLED co" : ", OLED KHONG tra loi");
    sb_puts(&sb, "\r\n");
    uart_puts(lb);
    note("$IDS,win,cls,alert,pkt,avg,syn%,src,dst,port,flags,lat,base,s0,s1,s2,susp,conf*CS");

    /* cau hinh phan cung */
    FEAT_PROT_NET  = PROT_NET;
    FEAT_PROT_MASK = PROT_MASK;
    FLT_BL_VALID   = 0;
    for (int i = 0; i < FLT_BL_SLOTS; i++) FLT_BL_IP(i) = 0;
    FLT_CNT_FWD    = 0;                  /* xoa 5 bo dem */
    syn_en = SYN_LIMIT_ON_BOOT;
    FLT_SYN_LIMIT  = SYN_LIMIT_PER_S;
    set_mode(MODE_ON_BOOT);
    if (syn_en) set_syn(1);
    /* bo cua so dang do (dem truoc khi dat PROT_NET) */
    FEAT_CTRL = FEAT_CTRL_ENABLE | FEAT_CTRL_ACK | FEAT_CTRL_CLR_OVR;

    oled_update();

    uint32_t next_sec = SYS_CYCLE + sec_cycles;
    for (;;) {
        if (FEAT_STATUS & FEAT_ST_READY)
            process_window();
        if ((int32_t)(SYS_CYCLE - next_sec) >= 0) {
            next_sec += sec_cycles;
            per_second();
        }
        button();
        oled_service();
    }
}
