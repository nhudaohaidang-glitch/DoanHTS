#ifndef AI_V3_INTEGRATION_H
#define AI_V3_INTEGRATION_H
#include "ai_quant_v3.h"
/* Return value is SAMPLE VALIDITY, not a class ID. Call the AI driver only
 * when this returns 1. Empty windows must not create a new block decision.
 * Use RAW packet count: 1..7 packets can have q0==0 and are still valid.
 * Existing block TTL/expiry runs independently, including during idle time. */
static inline int ai_v3_prepare_window(uint32_t packets, uint64_t ip_bytes,
    uint32_t syn_open, uint32_t src_count, uint32_t dst_count,
    uint32_t port_count, uint64_t *feat_out) {
    if (!feat_out) return 0;
    *feat_out = 0;
    if (packets == 0u) return 0;
    *feat_out = ai_v3_pack(packets, ip_bytes, syn_open,
                           src_count, dst_count, port_count);
    return 1;
}
#endif
