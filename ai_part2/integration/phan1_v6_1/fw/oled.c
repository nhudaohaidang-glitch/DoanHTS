/* =============================================================================
 * oled.c - Driver SSD1306 (I2C bit-bang, che do dia chi trang) + bo dem chu 8x21
 * I2C kieu cuc mang ho: ghi 1 vao bit = keo chan xuong 0, ghi 0 = tha noi (dien tro keo
 * len tren module dua len 1). Khong dung keo dai xung clock (SSD1306 khong dung).
 * Chay duoc ca voi man SH1106 (132 cot) neu dat OLED_COL_OFFSET = 2 trong config.h.
 * ========================================================================== */
#include "oled.h"
#include "hw.h"
#include "config.h"

#ifndef OLED_COL_OFFSET
#define OLED_COL_OFFSET 0
#endif

extern const uint8_t font5x7[95][5];

static int      present;
static char     text[OLED_LINES][OLED_COLS];
static uint8_t  dirty;                           /* bit i = dong i can ve lai             */

/* ---------------------------------------------------------------- I2C muc thap
 * Moi lan ghi thanh ghi dat CA HAI chan: bit0 = keo SCL xuong, bit1 = keo SDA xuong.
 * SDA chi doi khi SCL dang thap (tru START/STOP). */
#define L_SCL  I2C_SCL_LOW
#define L_SDA  I2C_SDA_LOW

static inline void bus(uint32_t v)
{
    SYS_OLED_I2C = v;
#if I2C_HALF_CYC > 0
    uint32_t t0 = SYS_CYCLE;
    while (SYS_CYCLE - t0 < I2C_HALF_CYC)
        ;
#endif
}

static void i2c_start(void)                      /* tu SCL thap hoac bus ranh */
{
    bus(0);                                      /* tha ca hai: SCL, SDA len 1 */
    bus(L_SDA);                                  /* SDA xuong khi SCL cao = START */
    bus(L_SDA | L_SCL);
}

static void i2c_stop(void)                       /* tu SCL thap */
{
    bus(L_SDA | L_SCL);
    bus(L_SDA);                                  /* SCL len */
    bus(0);                                      /* SDA len khi SCL cao = STOP */
}

static int i2c_write(uint32_t b)                 /* tra ve 1 neu thiet bi ACK */
{
    for (int i = 0; i < 8; i++) {
        uint32_t d = (b & 0x80u) ? 0u : L_SDA;
        bus(d | L_SCL);                          /* dat bit khi SCL thap */
        bus(d);                                  /* SCL len: thiet bi doc bit */
        bus(d | L_SCL);
        b <<= 1;
    }
    bus(L_SCL);                                  /* tha SDA cho thiet bi tra loi */
    bus(0);
    int ack = (SYS_OLED_I2C & I2C_SDA_IN) == 0;
    bus(L_SCL);
    return ack;
}

/* ---------------------------------------------------------------- lenh SSD1306 */
static int oled_cmds(const uint8_t *c, int n)
{
    i2c_start();
    int ok = i2c_write((uint8_t)(OLED_ADDR << 1));
    if (ok) {
        i2c_write(0x00);                         /* byte dieu khien: chuoi lenh */
        for (int i = 0; i < n; i++)
            i2c_write(c[i]);
    }
    i2c_stop();
    return ok;
}

static void draw_line(int line)
{
    const uint8_t pos[3] = { (uint8_t)(0xB0 | line),                    /* trang (dong) */
                             (uint8_t)(0x00 | (OLED_COL_OFFSET & 0x0F)), /* cot thap     */
                             (uint8_t)(0x10 | (OLED_COL_OFFSET >> 4)) }; /* cot cao      */
    oled_cmds(pos, 3);
    i2c_start();
    i2c_write((uint8_t)(OLED_ADDR << 1));
    i2c_write(0x40);                             /* byte dieu khien: du lieu anh */
    for (int c = 0; c < OLED_COLS; c++) {
        uint8_t ch = (uint8_t)text[line][c];
        if (ch < 0x20 || ch > 0x7E) ch = '?';
        const uint8_t *g = font5x7[ch - 0x20];
        for (int k = 0; k < 5; k++)
            i2c_write(g[k]);
        i2c_write(0x00);                         /* cot trong giua 2 chu */
    }
    i2c_write(0x00);                             /* 21 x 6 = 126 cot, them 2 cot cho du 128 */
    i2c_write(0x00);
    i2c_stop();
}

/* ---------------------------------------------------------------- giao dien */
int oled_init(void)
{
    static const uint8_t init_seq[] = {
        0xAE,             /* tat man                          */
        0xD5, 0x80,       /* tan so dao dong / chia clock     */
        0xA8, 0x3F,       /* 64 dong                          */
        0xD3, 0x00,       /* khong lech dong                  */
        0x40,             /* dong bat dau = 0                 */
        0x8D, 0x14,       /* bat bom dien tich (charge pump)  */
        0x20, 0x02,       /* che do dia chi trang             */
        0xA1,             /* dao cot (module thuong lap nguoc) */
        0xC8,             /* quet COM tu duoi len             */
        0xDA, 0x12,       /* cau hinh chan COM cho 128x64     */
        0x81, 0xCF,       /* do tuong phan                    */
        0xD9, 0xF1,       /* thoi gian nap truoc              */
        0xDB, 0x40,       /* muc VCOMH                        */
        0xA4,             /* hien noi dung RAM                */
        0xA6,             /* khong dao mau                    */
        0xAF              /* bat man                          */
    };
    bus(L_SCL);                                  /* tu bus ranh: keo SCL truoc, roi STOP */
    i2c_stop();
    present = oled_cmds(init_seq, (int)sizeof(init_seq));
    for (int l = 0; l < OLED_LINES; l++)
        for (int c = 0; c < OLED_COLS; c++)
            text[l][c] = ' ';
    dirty = present ? 0xFF : 0;                  /* xoa ca man o lan ve dau */
    return present;
}

int oled_ok(void) { return present; }

void oled_set_line(int line, const char *s)
{
    if (line < 0 || line >= OLED_LINES)
        return;
    int changed = 0;
    for (int c = 0; c < OLED_COLS; c++) {
        char ch = *s ? *s++ : ' ';
        if (text[line][c] != ch) {
            text[line][c] = ch;
            changed = 1;
        }
    }
    if (changed && present)
        dirty |= (uint8_t)(1u << line);
}

int oled_pending(void)
{
    int n = 0;
    for (int l = 0; l < OLED_LINES; l++)
        n += (dirty >> l) & 1;
    return n;
}

int oled_service(void)
{
    static int next;                             /* xoay vong: dong nao cung den luot */
    if (!dirty)
        return 0;
    for (int k = 0; k < OLED_LINES; k++) {
        int l = (next + k) & (OLED_LINES - 1);
        if (dirty & (1u << l)) {
            dirty &= (uint8_t)~(1u << l);
            draw_line(l);
            next = (l + 1) & (OLED_LINES - 1);
            return 1;
        }
    }
    return 0;
}
