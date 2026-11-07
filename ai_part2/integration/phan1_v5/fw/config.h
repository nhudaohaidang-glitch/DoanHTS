/* =============================================================================
 * config.h - Thong so chinh sach cua tuong lua. Sua o day roi bien dich lai firmware.
 * Ban mo phong (build_fw.sh tao firmware_sim.hex) duoc bien dich voi -DSIM_FAST:
 * thoi gian chan ngan hon va I2C khong cho, de testbench chay nhanh.
 * ========================================================================== */
#ifndef CONFIG_H
#define CONFIG_H

#define IP4(a, b, c, d)   (((uint32_t)(a) << 24) | ((uint32_t)(b) << 16) | ((uint32_t)(c) << 8) | (uint32_t)(d))

/* ---- Mang can bao ve: chi dem goi di VAO dia chi nay (de goi broadcast, multicast
 *      va goi giua cac may ben ngoai khong lam sai dac trung). Mac dinh: rieng broker. */
#define PROT_NET          IP4(192, 168, 10, 2)
#define PROT_MASK         IP4(255, 255, 255, 255)

/* ---- Danh sach trang: khong bao gio chan */
#define ALLOW_LIST        { IP4(192, 168, 10, 2),    /* Laptop trong (broker)  */ \
                            IP4(192, 168, 10, 20) }  /* may ao cam bien        */

/* ---- Lop 3 (AI + CPU) */
#define ALERT_ON_N        2      /* so cua so tan cong lien tiep moi bao dong / chan  */
#define BLOCK_TTL_S       60     /* giay; het han thi tu go                          */
#define AI_TIMEOUT_CYC    2000u  /* AI v5 can 84 chu ky; qua 2000 coi nhu treo          */

/* ---- Cong kiem tra hop ly cho ket qua AI (lop an toan cua firmware truoc khi chan).
 *      Dat ve 0 de tat. Moi lan cong doi ket qua deu duoc danh dau o bit4 cua flags. */
#define SCAN_MIN_PORTS    3      /* "quet cong" phai cham >= 3 cong dich khac nhau    */
#define DOS_MIN_SYN       20     /* "SYN flood" phai co >= 20 goi SYN trong cua so    */

/* ---- Lop 2: gioi han SYN (tat khi khoi dong; nhan giu S1 >= 2 s de bat/tat) */
#define SYN_LIMIT_PER_S   200
#define SYN_LIMIT_ON_BOOT 0

/* ---- Che do luc khoi dong: 0 = chi phat hien, 1 = chan */
#define MODE_ON_BOOT      0

/* ---- Nut S1 */
#define LONG_PRESS_MS     2000   /* tinh theo "giay" phan cung (SEC_CYCLES), nen mo phong cung dung */

/* ---- Man OLED SSD1306 */
#define OLED_ADDR         0x3C   /* mot so module la 0x3D */
#define I2C_HALF_CYC      10     /* cho them ~10 chu ky moi lan doi muc chan -> SCL ~80-90 kHz o 27 MHz */
#define OLED_COL_OFFSET   0      /* man SH1106 (132 cot) thi dat 2                    */

#ifdef SIM_FAST
#undef  BLOCK_TTL_S
#define BLOCK_TTL_S       6
#undef  I2C_HALF_CYC
#define I2C_HALF_CYC      0
#endif

#endif
