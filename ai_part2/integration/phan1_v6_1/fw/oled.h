/* =============================================================================
 * oled.h - Man OLED SSD1306 128x64 qua I2C (bit-bang tren thanh ghi SYS_OLED_I2C)
 * Man chia 8 dong x 21 ky tu (font 5x7 + 1 cot trong). Firmware giu noi dung chu cua
 * 8 dong trong RAM; oled_service() ve lai DUNG 1 dong co thay doi moi lan goi, de vong
 * lap chinh khong bi chan lau (1 dong ~ 12 ms o 100 kHz).
 * ========================================================================== */
#ifndef OLED_H
#define OLED_H
#include <stdint.h>

#define OLED_LINES 8
#define OLED_COLS  21

int  oled_init(void);                           /* 1 = man tra loi (ACK), 0 = khong co man */
int  oled_ok(void);
void oled_set_line(int line, const char *s);    /* chi danh dau "can ve" neu noi dung doi */
int  oled_service(void);                        /* ve 1 dong can ve; tra ve 1 neu da ve    */
int  oled_pending(void);                        /* so dong dang cho ve                    */
#endif
