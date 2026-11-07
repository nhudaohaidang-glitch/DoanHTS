#ifndef AI_V5_INTEGRATION_H
#define AI_V5_INTEGRATION_H
#include "ai_quant_v5.h"
/* Validity is RAW packet count, not q0. TTL is handled by the caller. */
static inline int ai_v5_prepare_window(uint32_t packets, uint64_t ip_bytes,
 uint32_t syn_open, uint32_t src_count, uint32_t dst_count,
 uint32_t port_count, uint64_t *feat_out) {
 *feat_out=0;
 if (!packets) return 0;
 *feat_out=ai_v5_pack(packets,ip_bytes,syn_open,src_count,dst_count,port_count);
 return 1;
}
#endif
