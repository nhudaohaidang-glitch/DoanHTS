#ifndef AI_V5_HANDOFF_VECTORS_H
#define AI_V5_HANDOFF_VECTORS_H
#include <stdint.h>
/* Numeric reference only. Bind to the real CPU register driver. */
#define AI_V5_MODEL_SHA256 "688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e"
typedef struct { const char *name; uint32_t packets; uint64_t ip_bytes; uint32_t syn, src, dst, ports;
 uint32_t feat_lo; uint16_t feat_hi; int16_t scores[3]; uint8_t class_id, valid; } ai_v5_check_vector_t;
static const ai_v5_check_vector_t ai_v5_check_vectors[] = {
 {"empty_skip", 0u, UINT64_C(0), 0u, 0u, 0u, 0u, UINT32_C(0x00000000), UINT16_C(0x0000), {0, 0, 0}, 255, 0},
 {"sensor_feedback", 7u, UINT64_C(427), 1u, 1u, 1u, 1u, UINT32_C(0x01121e00), UINT16_C(0x0101), {5606, -2278, -3298}, 0, 1},
 {"single_legitimate_syn", 1u, UINT64_C(40), 1u, 1u, 1u, 1u, UINT32_C(0x017f1400), UINT16_C(0x0101), {225, -457, 225}, 0, 1},
 {"ack52_1", 1u, UINT64_C(52), 0u, 1u, 1u, 1u, UINT32_C(0x01001a00), UINT16_C(0x0101), {6308, -2518, -3754}, 0, 1},
 {"ack52_7", 7u, UINT64_C(364), 0u, 1u, 1u, 1u, UINT32_C(0x01001a00), UINT16_C(0x0101), {6308, -2518, -3754}, 0, 1},
 {"ack52_8", 8u, UINT64_C(416), 0u, 1u, 1u, 1u, UINT32_C(0x01001a01), UINT16_C(0x0101), {6308, -2518, -3754}, 0, 1},
 {"ack52_30", 30u, UINT64_C(1560), 0u, 1u, 1u, 1u, UINT32_C(0x01001a03), UINT16_C(0x0101), {6308, -2518, -3754}, 0, 1},
 {"ack52_100", 100u, UINT64_C(5200), 0u, 1u, 1u, 1u, UINT32_C(0x01001a0c), UINT16_C(0x0101), {6260, -2508, -3715}, 0, 1},
 {"ack52_1000", 1000u, UINT64_C(52000), 0u, 1u, 1u, 1u, UINT32_C(0x01001a7d), UINT16_C(0x0101), {5797, -1249, -4536}, 0, 1},
 {"pure_vertical_scan_3", 3u, UINT64_C(120), 3u, 1u, 1u, 3u, UINT32_C(0x017f1400), UINT16_C(0x0301), {158, -468, 305}, 2, 1},
 {"pure_vertical_scan_4", 4u, UINT64_C(160), 4u, 1u, 1u, 4u, UINT32_C(0x017f1400), UINT16_C(0x0401), {158, -468, 305}, 2, 1},
 {"pure_vertical_scan_5", 5u, UINT64_C(200), 5u, 1u, 1u, 5u, UINT32_C(0x017f1400), UINT16_C(0x0501), {56, -428, 365}, 2, 1},
 {"pure_vertical_scan_6", 6u, UINT64_C(240), 6u, 1u, 1u, 6u, UINT32_C(0x017f1400), UINT16_C(0x0601), {8, -418, 404}, 2, 1},
 {"pure_vertical_scan_7", 7u, UINT64_C(280), 7u, 1u, 1u, 7u, UINT32_C(0x017f1400), UINT16_C(0x0701), {8, -418, 404}, 2, 1},
 {"pure_vertical_scan_8", 8u, UINT64_C(320), 8u, 1u, 1u, 8u, UINT32_C(0x017f1401), UINT16_C(0x0801), {8, -418, 404}, 2, 1},
 {"pure_vertical_scan_9", 9u, UINT64_C(360), 9u, 1u, 1u, 9u, UINT32_C(0x017f1401), UINT16_C(0x0901), {-94, -378, 464}, 2, 1},
 {"pure_vertical_scan_10", 10u, UINT64_C(400), 10u, 1u, 1u, 10u, UINT32_C(0x017f1401), UINT16_C(0x0a01), {-142, -368, 503}, 2, 1},
 {"pure_vertical_scan_11", 11u, UINT64_C(440), 11u, 1u, 1u, 11u, UINT32_C(0x017f1401), UINT16_C(0x0b01), {-142, -368, 503}, 2, 1},
 {"pure_vertical_scan_12", 12u, UINT64_C(480), 12u, 1u, 1u, 12u, UINT32_C(0x017f1401), UINT16_C(0x0c01), {-142, -368, 503}, 2, 1},
 {"pure_vertical_scan_13", 13u, UINT64_C(520), 13u, 1u, 1u, 13u, UINT32_C(0x017f1401), UINT16_C(0x0d01), {-244, -328, 563}, 2, 1},
 {"pure_vertical_scan_14", 14u, UINT64_C(560), 14u, 1u, 1u, 14u, UINT32_C(0x017f1401), UINT16_C(0x0e01), {-244, -328, 563}, 2, 1},
 {"pure_vertical_scan_15", 15u, UINT64_C(600), 15u, 1u, 1u, 15u, UINT32_C(0x017f1401), UINT16_C(0x0f01), {-244, -328, 563}, 2, 1},
 {"pure_vertical_scan_16", 16u, UINT64_C(640), 16u, 1u, 1u, 16u, UINT32_C(0x017f1402), UINT16_C(0x1001), {-244, -328, 563}, 2, 1},
 {"pure_vertical_scan_17", 17u, UINT64_C(680), 17u, 1u, 1u, 17u, UINT32_C(0x017f1402), UINT16_C(0x1101), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_18", 18u, UINT64_C(720), 18u, 1u, 1u, 18u, UINT32_C(0x017f1402), UINT16_C(0x1201), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_19", 19u, UINT64_C(760), 19u, 1u, 1u, 19u, UINT32_C(0x017f1402), UINT16_C(0x1301), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_20", 20u, UINT64_C(800), 20u, 1u, 1u, 20u, UINT32_C(0x017f1402), UINT16_C(0x1401), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_21", 21u, UINT64_C(840), 21u, 1u, 1u, 21u, UINT32_C(0x017f1402), UINT16_C(0x1501), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_22", 22u, UINT64_C(880), 22u, 1u, 1u, 22u, UINT32_C(0x017f1402), UINT16_C(0x1601), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_23", 23u, UINT64_C(920), 23u, 1u, 1u, 23u, UINT32_C(0x017f1402), UINT16_C(0x1701), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_24", 24u, UINT64_C(960), 24u, 1u, 1u, 24u, UINT32_C(0x017f1403), UINT16_C(0x1801), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_25", 25u, UINT64_C(1000), 25u, 1u, 1u, 25u, UINT32_C(0x017f1403), UINT16_C(0x1901), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_26", 26u, UINT64_C(1040), 26u, 1u, 1u, 26u, UINT32_C(0x017f1403), UINT16_C(0x1a01), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_27", 27u, UINT64_C(1080), 27u, 1u, 1u, 27u, UINT32_C(0x017f1403), UINT16_C(0x1b01), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_28", 28u, UINT64_C(1120), 28u, 1u, 1u, 28u, UINT32_C(0x017f1403), UINT16_C(0x1c01), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_29", 29u, UINT64_C(1160), 29u, 1u, 1u, 29u, UINT32_C(0x017f1403), UINT16_C(0x1d01), {-346, -288, 623}, 2, 1},
 {"pure_vertical_scan_30", 30u, UINT64_C(1200), 30u, 1u, 1u, 30u, UINT32_C(0x017f1403), UINT16_C(0x1e01), {-346, -288, 623}, 2, 1},
};
#define AI_V5_CHECK_VECTOR_COUNT (sizeof(ai_v5_check_vectors)/sizeof(ai_v5_check_vectors[0]))
#endif
