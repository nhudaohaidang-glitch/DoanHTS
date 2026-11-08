/* =============================================================================
 * uart.h - Gui chuoi qua UART va ghep chuoi vao bo dem
 * ========================================================================== */
#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_putc(char c);
void uart_puts(const char *s);

/* Ghep chuoi vao bo dem (khong dung printf de firmware gon) */
typedef struct {
    char    *buf;
    uint32_t len;
    uint32_t cap;
} strbuf_t;

void sb_init(strbuf_t *sb, char *buf, uint32_t cap);
void sb_putc(strbuf_t *sb, char c);
void sb_puts(strbuf_t *sb, const char *s);
void sb_u32(strbuf_t *sb, uint32_t v);          /* so thap phan khong dau */
void sb_hex(strbuf_t *sb, uint32_t v, int digits);

#endif
