/* Example adapter: produces words only; no bus/MMIO code from another member. */
#include "ai_v6_integration.h"
int ai_prepare_words(uint32_t packets, uint64_t total_ip_bytes, uint32_t syn_open,
 uint32_t src_count, uint32_t dst_count, uint32_t port_count,
 uint32_t *feat_lo, uint32_t *feat_hi) {
 uint64_t feat;
 int valid=ai_v6_prepare_window(packets,total_ip_bytes,syn_open,src_count,dst_count,port_count,&feat);
 *feat_lo=(uint32_t)feat;
 *feat_hi=(uint32_t)(feat>>32);
 return valid; /* Caller skips START when valid==0. */
}
