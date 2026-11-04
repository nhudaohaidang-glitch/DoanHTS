/* =============================================================================
 * hw.h - Ban do thanh ghi phan cung (khop voi rtl/gateway_soc.v va rtl/wb_*.v)
 * Phien ban tuong lua Ethernet.
 * ========================================================================== */
#ifndef HW_H
#define HW_H

#include <stdint.h>

#define REG32(addr)        (*(volatile uint32_t *)(addr))

/* ---------------- UART TX (log len Laptop trong): 0x1000_0000 ---------------- */
#define UART_BASE          0x10000000u
#define UART_DATA          REG32(UART_BASE + 0x00)   /* W: gui 1 byte            */
#define UART_STATUS        REG32(UART_BASE + 0x04)   /* R: bit0 = dang ban       */
#define UART_BUSY          (1u << 0)

/* ---------------- Khoi dac trung (Phan 3): 0x2000_0000 ---------------- */
#define FEAT_BASE          0x20000000u
#define FEAT_STATUS        REG32(FEAT_BASE + 0x00)
#define FEAT_CTRL          REG32(FEAT_BASE + 0x04)
#define FEAT_WIN_ID        REG32(FEAT_BASE + 0x08)
#define FEAT_PKT_CNT       REG32(FEAT_BASE + 0x0C)   /* raw f0: so goi              */
#define FEAT_BYTE_SUM      REG32(FEAT_BASE + 0x10)   /* tong IPv4 Total Length      */
#define FEAT_SYN_CNT       REG32(FEAT_BASE + 0x14)   /* so goi SYN=1, ACK=0         */
#define FEAT_SRC_IP        REG32(FEAT_BASE + 0x18)   /* raw f3                      */
#define FEAT_DST_IP        REG32(FEAT_BASE + 0x1C)   /* raw f4                      */
#define FEAT_DST_PORT      REG32(FEAT_BASE + 0x20)   /* raw f5                      */
#define FEAT_ERR_CNT       REG32(FEAT_BASE + 0x24)
#define FEAT_SUSPECT_IP    REG32(FEAT_BASE + 0x28)   /* IP nghi van (chon o cua so truoc) */
#define FEAT_CONFIRM_CNT   REG32(FEAT_BASE + 0x2C)   /* SYN tu dung IP do trong cua so nay */
#define FEAT_PROT_NET      REG32(FEAT_BASE + 0x30)
#define FEAT_PROT_MASK     REG32(FEAT_BASE + 0x34)
#define FEAT_ST_READY      (1u << 0)
#define FEAT_ST_OVERRUN    (1u << 1)
#define FEAT_CTRL_ACK      (1u << 0)
#define FEAT_CTRL_CLR_OVR  (1u << 1)
#define FEAT_CTRL_ENABLE   (1u << 8)

/* ---------------- AI accelerator V5 (Phan 2): 0x3000_0000 ---------------- */
#define AI_BASE            0x30000000u
#define AI_STATUS          REG32(AI_BASE + 0x00)
#define AI_CTRL            REG32(AI_BASE + 0x04)
#define AI_FEAT_LO         REG32(AI_BASE + 0x08)     /* q0..q3, q0 o bit 7:0      */
#define AI_FEAT_HI         REG32(AI_BASE + 0x0C)     /* q4..q5                    */
#define AI_RESULT          REG32(AI_BASE + 0x10)     /* 0 BT, 1 SYN flood, 2 quet  */
#define AI_SCORE0          REG32(AI_BASE + 0x14)     /* int16 co dau, da mo rong dau */
#define AI_SCORE1          REG32(AI_BASE + 0x18)
#define AI_SCORE2          REG32(AI_BASE + 0x1C)
#define AI_LAT             REG32(AI_BASE + 0x20)
#define AI_ST_BUSY         (1u << 0)
#define AI_ST_DONE         (1u << 1)
#define AI_CTRL_START      (1u << 0)
#define AI_CTRL_ABORT      (1u << 1)

/* ---------------- He thong: 0x4000_0000 ---------------- */
#define SYS_BASE           0x40000000u
#define SYS_CYCLE          REG32(SYS_BASE + 0x04)    /* dem chu ky clock          */
#define SYS_OLED_I2C       REG32(SYS_BASE + 0x08)    /* W bit0 keo SCL, bit1 keo SDA; R bit8 SCL, bit9 SDA */
#define SYS_BTN            REG32(SYS_BASE + 0x0C)    /* bit0 = dang nhan S1       */
#define SYS_ID             REG32(SYS_BASE + 0x10)    /* 0x52563332 "RV32"         */
#define SYS_SCRATCH        REG32(SYS_BASE + 0x14)
#define SYS_REFA_HZ        REG32(SYS_BASE + 0x18)    /* tan so REF_CLK cong A     */
#define SYS_REFB_HZ        REG32(SYS_BASE + 0x1C)
#define SYS_SEC_CYCLES     REG32(SYS_BASE + 0x20)    /* so chu ky cua 1 giay      */
#define SYS_ID_VALUE       0x52563332u
#define I2C_SCL_LOW        (1u << 0)
#define I2C_SDA_LOW        (1u << 1)
#define I2C_SCL_IN         (1u << 8)
#define I2C_SDA_IN         (1u << 9)

/* ---------------- Bo loc (Phan 3): 0x5000_0000 ---------------- */
#define FLT_BASE           0x50000000u
#define FLT_CTRL           REG32(FLT_BASE + 0x00)    /* bit0 BL_EN, bit1 SYN_EN   */
#define FLT_SYN_LIMIT      REG32(FLT_BASE + 0x04)    /* goi SYN toi da moi giay   */
#define FLT_BL_VALID       REG32(FLT_BASE + 0x08)    /* bit i = o i dang dung     */
#define FLT_BL_IP(i)       REG32(FLT_BASE + 0x10 + 4u * (uint32_t)(i))   /* CHI GHI, doc ra 0 */
#define FLT_CNT_FWD        REG32(FLT_BASE + 0x40)    /* ghi bat ky = xoa ca 5 bo dem */
#define FLT_CNT_DROP_BL    REG32(FLT_BASE + 0x44)
#define FLT_CNT_DROP_SYN   REG32(FLT_BASE + 0x48)
#define FLT_CNT_CRC_ERR    REG32(FLT_BASE + 0x4C)
#define FLT_CNT_OVERFLOW   REG32(FLT_BASE + 0x50)
#define FLT_CTRL_BL_EN     (1u << 0)
#define FLT_CTRL_SYN_EN    (1u << 1)
#define FLT_BL_SLOTS       8

#endif
