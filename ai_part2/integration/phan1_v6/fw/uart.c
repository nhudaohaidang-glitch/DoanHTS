/* =============================================================================
 * uart.c - Gui chuoi qua UART va ghep chuoi vao bo dem
 * ========================================================================== */
#include "uart.h"
#include "hw.h"

void uart_putc(char c)
{
    while (UART_STATUS & UART_BUSY)
        ;                                   /* cho gui xong byte truoc */
    UART_DATA = (uint8_t)c;
}

void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

void sb_init(strbuf_t *sb, char *buf, uint32_t cap)
{
    sb->buf = buf;
    sb->len = 0;
    sb->cap = cap;
    buf[0] = '\0';
}

void sb_putc(strbuf_t *sb, char c)
{
    if (sb->len + 1 < sb->cap) {
        sb->buf[sb->len++] = c;
        sb->buf[sb->len] = '\0';
    }
}

void sb_puts(strbuf_t *sb, const char *s)
{
    while (*s)
        sb_putc(sb, *s++);
}

/* In so thap phan bang phep tru luy thua cua 10: tranh phep chia (cham tren RV32I) */
void sb_u32(strbuf_t *sb, uint32_t v)
{
    static const uint32_t pow10[] = { 1000000000u, 100000000u, 10000000u, 1000000u,
                                      100000u, 10000u, 1000u, 100u, 10u, 1u };
    int started = 0;
    for (int i = 0; i < 10; i++) {
        char d = '0';
        while (v >= pow10[i]) {
            v -= pow10[i];
            d++;
        }
        if (d != '0' || started || i == 9) {
            sb_putc(sb, d);
            started = 1;
        }
    }
}

void sb_hex(strbuf_t *sb, uint32_t v, int digits)
{
    static const char hex[] = "0123456789ABCDEF";
    for (int i = digits - 1; i >= 0; i--)
        sb_putc(sb, hex[(v >> (4 * i)) & 0xF]);
}
