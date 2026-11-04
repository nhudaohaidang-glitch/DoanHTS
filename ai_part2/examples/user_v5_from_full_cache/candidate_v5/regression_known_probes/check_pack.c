#include <stdint.h>
#include <stdio.h>
#include "ai_quant_v5.h"
int main(void) {
    unsigned failures = 0;
    /* sensor_feedback: aggregate consistent with this raw probe. */
    if (ai_v5_pack(7u, UINT64_C(427), 1u, 1u, 1u, 1u)
        != UINT64_C(0x010101121e00)) { puts("PACK MISMATCH sensor_feedback"); ++failures; }
    /* single_legitimate_syn: aggregate consistent with this raw probe. */
    if (ai_v5_pack(1u, UINT64_C(40), 1u, 1u, 1u, 1u)
        != UINT64_C(0x0101017f1400)) { puts("PACK MISMATCH single_legitimate_syn"); ++failures; }
    /* ack52_1: aggregate consistent with this raw probe. */
    if (ai_v5_pack(1u, UINT64_C(52), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a00)) { puts("PACK MISMATCH ack52_1"); ++failures; }
    /* ack52_7: aggregate consistent with this raw probe. */
    if (ai_v5_pack(7u, UINT64_C(364), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a00)) { puts("PACK MISMATCH ack52_7"); ++failures; }
    /* ack52_8: aggregate consistent with this raw probe. */
    if (ai_v5_pack(8u, UINT64_C(416), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a01)) { puts("PACK MISMATCH ack52_8"); ++failures; }
    /* ack52_30: aggregate consistent with this raw probe. */
    if (ai_v5_pack(30u, UINT64_C(1560), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a03)) { puts("PACK MISMATCH ack52_30"); ++failures; }
    /* ack52_100: aggregate consistent with this raw probe. */
    if (ai_v5_pack(100u, UINT64_C(5200), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a0c)) { puts("PACK MISMATCH ack52_100"); ++failures; }
    /* ack52_1000: aggregate consistent with this raw probe. */
    if (ai_v5_pack(1000u, UINT64_C(52000), 0u, 1u, 1u, 1u)
        != UINT64_C(0x010101001a7d)) { puts("PACK MISMATCH ack52_1000"); ++failures; }
    /* pure_vertical_scan_3: aggregate consistent with this raw probe. */
    if (ai_v5_pack(3u, UINT64_C(120), 3u, 1u, 1u, 3u)
        != UINT64_C(0x0301017f1400)) { puts("PACK MISMATCH pure_vertical_scan_3"); ++failures; }
    /* pure_vertical_scan_4: aggregate consistent with this raw probe. */
    if (ai_v5_pack(4u, UINT64_C(160), 4u, 1u, 1u, 4u)
        != UINT64_C(0x0401017f1400)) { puts("PACK MISMATCH pure_vertical_scan_4"); ++failures; }
    /* pure_vertical_scan_5: aggregate consistent with this raw probe. */
    if (ai_v5_pack(5u, UINT64_C(200), 5u, 1u, 1u, 5u)
        != UINT64_C(0x0501017f1400)) { puts("PACK MISMATCH pure_vertical_scan_5"); ++failures; }
    /* pure_vertical_scan_6: aggregate consistent with this raw probe. */
    if (ai_v5_pack(6u, UINT64_C(240), 6u, 1u, 1u, 6u)
        != UINT64_C(0x0601017f1400)) { puts("PACK MISMATCH pure_vertical_scan_6"); ++failures; }
    /* pure_vertical_scan_7: aggregate consistent with this raw probe. */
    if (ai_v5_pack(7u, UINT64_C(280), 7u, 1u, 1u, 7u)
        != UINT64_C(0x0701017f1400)) { puts("PACK MISMATCH pure_vertical_scan_7"); ++failures; }
    /* pure_vertical_scan_8: aggregate consistent with this raw probe. */
    if (ai_v5_pack(8u, UINT64_C(320), 8u, 1u, 1u, 8u)
        != UINT64_C(0x0801017f1401)) { puts("PACK MISMATCH pure_vertical_scan_8"); ++failures; }
    /* pure_vertical_scan_9: aggregate consistent with this raw probe. */
    if (ai_v5_pack(9u, UINT64_C(360), 9u, 1u, 1u, 9u)
        != UINT64_C(0x0901017f1401)) { puts("PACK MISMATCH pure_vertical_scan_9"); ++failures; }
    /* pure_vertical_scan_10: aggregate consistent with this raw probe. */
    if (ai_v5_pack(10u, UINT64_C(400), 10u, 1u, 1u, 10u)
        != UINT64_C(0x0a01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_10"); ++failures; }
    /* pure_vertical_scan_11: aggregate consistent with this raw probe. */
    if (ai_v5_pack(11u, UINT64_C(440), 11u, 1u, 1u, 11u)
        != UINT64_C(0x0b01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_11"); ++failures; }
    /* pure_vertical_scan_12: aggregate consistent with this raw probe. */
    if (ai_v5_pack(12u, UINT64_C(480), 12u, 1u, 1u, 12u)
        != UINT64_C(0x0c01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_12"); ++failures; }
    /* pure_vertical_scan_13: aggregate consistent with this raw probe. */
    if (ai_v5_pack(13u, UINT64_C(520), 13u, 1u, 1u, 13u)
        != UINT64_C(0x0d01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_13"); ++failures; }
    /* pure_vertical_scan_14: aggregate consistent with this raw probe. */
    if (ai_v5_pack(14u, UINT64_C(560), 14u, 1u, 1u, 14u)
        != UINT64_C(0x0e01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_14"); ++failures; }
    /* pure_vertical_scan_15: aggregate consistent with this raw probe. */
    if (ai_v5_pack(15u, UINT64_C(600), 15u, 1u, 1u, 15u)
        != UINT64_C(0x0f01017f1401)) { puts("PACK MISMATCH pure_vertical_scan_15"); ++failures; }
    /* pure_vertical_scan_16: aggregate consistent with this raw probe. */
    if (ai_v5_pack(16u, UINT64_C(640), 16u, 1u, 1u, 16u)
        != UINT64_C(0x1001017f1402)) { puts("PACK MISMATCH pure_vertical_scan_16"); ++failures; }
    /* pure_vertical_scan_17: aggregate consistent with this raw probe. */
    if (ai_v5_pack(17u, UINT64_C(680), 17u, 1u, 1u, 17u)
        != UINT64_C(0x1101017f1402)) { puts("PACK MISMATCH pure_vertical_scan_17"); ++failures; }
    /* pure_vertical_scan_18: aggregate consistent with this raw probe. */
    if (ai_v5_pack(18u, UINT64_C(720), 18u, 1u, 1u, 18u)
        != UINT64_C(0x1201017f1402)) { puts("PACK MISMATCH pure_vertical_scan_18"); ++failures; }
    /* pure_vertical_scan_19: aggregate consistent with this raw probe. */
    if (ai_v5_pack(19u, UINT64_C(760), 19u, 1u, 1u, 19u)
        != UINT64_C(0x1301017f1402)) { puts("PACK MISMATCH pure_vertical_scan_19"); ++failures; }
    /* pure_vertical_scan_20: aggregate consistent with this raw probe. */
    if (ai_v5_pack(20u, UINT64_C(800), 20u, 1u, 1u, 20u)
        != UINT64_C(0x1401017f1402)) { puts("PACK MISMATCH pure_vertical_scan_20"); ++failures; }
    /* pure_vertical_scan_21: aggregate consistent with this raw probe. */
    if (ai_v5_pack(21u, UINT64_C(840), 21u, 1u, 1u, 21u)
        != UINT64_C(0x1501017f1402)) { puts("PACK MISMATCH pure_vertical_scan_21"); ++failures; }
    /* pure_vertical_scan_22: aggregate consistent with this raw probe. */
    if (ai_v5_pack(22u, UINT64_C(880), 22u, 1u, 1u, 22u)
        != UINT64_C(0x1601017f1402)) { puts("PACK MISMATCH pure_vertical_scan_22"); ++failures; }
    /* pure_vertical_scan_23: aggregate consistent with this raw probe. */
    if (ai_v5_pack(23u, UINT64_C(920), 23u, 1u, 1u, 23u)
        != UINT64_C(0x1701017f1402)) { puts("PACK MISMATCH pure_vertical_scan_23"); ++failures; }
    /* pure_vertical_scan_24: aggregate consistent with this raw probe. */
    if (ai_v5_pack(24u, UINT64_C(960), 24u, 1u, 1u, 24u)
        != UINT64_C(0x1801017f1403)) { puts("PACK MISMATCH pure_vertical_scan_24"); ++failures; }
    /* pure_vertical_scan_25: aggregate consistent with this raw probe. */
    if (ai_v5_pack(25u, UINT64_C(1000), 25u, 1u, 1u, 25u)
        != UINT64_C(0x1901017f1403)) { puts("PACK MISMATCH pure_vertical_scan_25"); ++failures; }
    /* pure_vertical_scan_26: aggregate consistent with this raw probe. */
    if (ai_v5_pack(26u, UINT64_C(1040), 26u, 1u, 1u, 26u)
        != UINT64_C(0x1a01017f1403)) { puts("PACK MISMATCH pure_vertical_scan_26"); ++failures; }
    /* pure_vertical_scan_27: aggregate consistent with this raw probe. */
    if (ai_v5_pack(27u, UINT64_C(1080), 27u, 1u, 1u, 27u)
        != UINT64_C(0x1b01017f1403)) { puts("PACK MISMATCH pure_vertical_scan_27"); ++failures; }
    /* pure_vertical_scan_28: aggregate consistent with this raw probe. */
    if (ai_v5_pack(28u, UINT64_C(1120), 28u, 1u, 1u, 28u)
        != UINT64_C(0x1c01017f1403)) { puts("PACK MISMATCH pure_vertical_scan_28"); ++failures; }
    /* pure_vertical_scan_29: aggregate consistent with this raw probe. */
    if (ai_v5_pack(29u, UINT64_C(1160), 29u, 1u, 1u, 29u)
        != UINT64_C(0x1d01017f1403)) { puts("PACK MISMATCH pure_vertical_scan_29"); ++failures; }
    /* pure_vertical_scan_30: aggregate consistent with this raw probe. */
    if (ai_v5_pack(30u, UINT64_C(1200), 30u, 1u, 1u, 30u)
        != UINT64_C(0x1e01017f1403)) { puts("PACK MISMATCH pure_vertical_scan_30"); ++failures; }
    printf("C packing: %u failures / 36 probes\n", failures);
    return failures ? 1 : 0;
}
