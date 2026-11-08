#include "ai_v5_integration.h"
volatile uint64_t saved;
int main(void) {
 uint64_t f=0; int bad=0;
 bad |= !ai_v5_prepare_window(1,40,1,1,1,1,&f) || f!=UINT64_C(0x0101017f1400);
 saved=f;
 bad |= ai_v5_prepare_window(0,0,0,0,0,0,&f) || f!=0;
 bad |= !ai_v5_prepare_window(7,280,7,1,1,1,&f) || f!=UINT64_C(0x0101017f1400);
 saved=f; return bad;
}
