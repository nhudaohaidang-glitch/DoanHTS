#ifndef AI_QUANT_V1_H
#define AI_QUANT_V1_H
#include <stdint.h>
/* Raw feature order and semantics: see spec/FEATURES_V0.md. */
static inline uint8_t ai_v1_clip(uint64_t x) { return x > 127u ? 127u : (uint8_t)x; }
static inline uint64_t ai_v1_pack(uint32_t packets, uint64_t ip_bytes, uint32_t syn_open,
                                  uint32_t src_count, uint32_t dst_count, uint32_t port_count) {
    if (!packets) return 0;
    uint64_t raw[6] = {packets, ip_bytes / packets,
                       (127ull * syn_open) / packets, src_count, dst_count, port_count};
    uint64_t feat = 0;
    feat |= (uint64_t)ai_v1_clip(raw[0] >> 3) << 0;
    feat |= (uint64_t)ai_v1_clip(raw[1] >> 0) << 8;
    feat |= (uint64_t)ai_v1_clip(raw[2] >> 0) << 16;
    feat |= (uint64_t)ai_v1_clip(raw[3] >> 0) << 24;
    feat |= (uint64_t)ai_v1_clip(raw[4] >> 0) << 32;
    feat |= (uint64_t)ai_v1_clip(raw[5] >> 2) << 40;
    return feat;
}
#endif
