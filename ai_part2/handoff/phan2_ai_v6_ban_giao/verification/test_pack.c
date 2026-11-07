/* Own part2 packing/validity test. No CPU, bus driver or system firmware. */
#include <stdio.h>
#include <stdint.h>
#include "ai_v6_integration.h"
int main(void) {
 unsigned errors=0; uint64_t feat=0; int valid;
 /* empty_skip */
 valid=ai_v6_prepare_window(0u,UINT64_C(0),0u,0u,0u,0u,&feat);
 if(valid!=0 || feat!=UINT64_C(0x000000000000)){ puts("FAIL empty_skip"); ++errors; }
 /* sensor_feedback */
 valid=ai_v6_prepare_window(7u,UINT64_C(427),1u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101121e00)){ puts("FAIL sensor_feedback"); ++errors; }
 /* single_legitimate_syn */
 valid=ai_v6_prepare_window(1u,UINT64_C(40),1u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0101017f1400)){ puts("FAIL single_legitimate_syn"); ++errors; }
 /* ack52_1 */
 valid=ai_v6_prepare_window(1u,UINT64_C(52),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a00)){ puts("FAIL ack52_1"); ++errors; }
 /* ack52_7 */
 valid=ai_v6_prepare_window(7u,UINT64_C(364),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a00)){ puts("FAIL ack52_7"); ++errors; }
 /* ack52_8 */
 valid=ai_v6_prepare_window(8u,UINT64_C(416),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a01)){ puts("FAIL ack52_8"); ++errors; }
 /* ack52_30 */
 valid=ai_v6_prepare_window(30u,UINT64_C(1560),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a03)){ puts("FAIL ack52_30"); ++errors; }
 /* ack52_100 */
 valid=ai_v6_prepare_window(100u,UINT64_C(5200),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a0c)){ puts("FAIL ack52_100"); ++errors; }
 /* ack52_1000 */
 valid=ai_v6_prepare_window(1000u,UINT64_C(52000),0u,1u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x010101001a7d)){ puts("FAIL ack52_1000"); ++errors; }
 /* pure_vertical_scan_3 */
 valid=ai_v6_prepare_window(3u,UINT64_C(120),3u,1u,1u,3u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0301017f1400)){ puts("FAIL pure_vertical_scan_3"); ++errors; }
 /* pure_vertical_scan_4 */
 valid=ai_v6_prepare_window(4u,UINT64_C(160),4u,1u,1u,4u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0401017f1400)){ puts("FAIL pure_vertical_scan_4"); ++errors; }
 /* pure_vertical_scan_5 */
 valid=ai_v6_prepare_window(5u,UINT64_C(200),5u,1u,1u,5u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0501017f1400)){ puts("FAIL pure_vertical_scan_5"); ++errors; }
 /* pure_vertical_scan_6 */
 valid=ai_v6_prepare_window(6u,UINT64_C(240),6u,1u,1u,6u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0601017f1400)){ puts("FAIL pure_vertical_scan_6"); ++errors; }
 /* pure_vertical_scan_7 */
 valid=ai_v6_prepare_window(7u,UINT64_C(280),7u,1u,1u,7u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0701017f1400)){ puts("FAIL pure_vertical_scan_7"); ++errors; }
 /* pure_vertical_scan_8 */
 valid=ai_v6_prepare_window(8u,UINT64_C(320),8u,1u,1u,8u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0801017f1401)){ puts("FAIL pure_vertical_scan_8"); ++errors; }
 /* pure_vertical_scan_9 */
 valid=ai_v6_prepare_window(9u,UINT64_C(360),9u,1u,1u,9u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0901017f1401)){ puts("FAIL pure_vertical_scan_9"); ++errors; }
 /* pure_vertical_scan_10 */
 valid=ai_v6_prepare_window(10u,UINT64_C(400),10u,1u,1u,10u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0a01017f1401)){ puts("FAIL pure_vertical_scan_10"); ++errors; }
 /* pure_vertical_scan_11 */
 valid=ai_v6_prepare_window(11u,UINT64_C(440),11u,1u,1u,11u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0b01017f1401)){ puts("FAIL pure_vertical_scan_11"); ++errors; }
 /* pure_vertical_scan_12 */
 valid=ai_v6_prepare_window(12u,UINT64_C(480),12u,1u,1u,12u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0c01017f1401)){ puts("FAIL pure_vertical_scan_12"); ++errors; }
 /* pure_vertical_scan_13 */
 valid=ai_v6_prepare_window(13u,UINT64_C(520),13u,1u,1u,13u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0d01017f1401)){ puts("FAIL pure_vertical_scan_13"); ++errors; }
 /* pure_vertical_scan_14 */
 valid=ai_v6_prepare_window(14u,UINT64_C(560),14u,1u,1u,14u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0e01017f1401)){ puts("FAIL pure_vertical_scan_14"); ++errors; }
 /* pure_vertical_scan_15 */
 valid=ai_v6_prepare_window(15u,UINT64_C(600),15u,1u,1u,15u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0f01017f1401)){ puts("FAIL pure_vertical_scan_15"); ++errors; }
 /* pure_vertical_scan_16 */
 valid=ai_v6_prepare_window(16u,UINT64_C(640),16u,1u,1u,16u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1001017f1402)){ puts("FAIL pure_vertical_scan_16"); ++errors; }
 /* pure_vertical_scan_17 */
 valid=ai_v6_prepare_window(17u,UINT64_C(680),17u,1u,1u,17u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1101017f1402)){ puts("FAIL pure_vertical_scan_17"); ++errors; }
 /* pure_vertical_scan_18 */
 valid=ai_v6_prepare_window(18u,UINT64_C(720),18u,1u,1u,18u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1201017f1402)){ puts("FAIL pure_vertical_scan_18"); ++errors; }
 /* pure_vertical_scan_19 */
 valid=ai_v6_prepare_window(19u,UINT64_C(760),19u,1u,1u,19u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1301017f1402)){ puts("FAIL pure_vertical_scan_19"); ++errors; }
 /* pure_vertical_scan_20 */
 valid=ai_v6_prepare_window(20u,UINT64_C(800),20u,1u,1u,20u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1401017f1402)){ puts("FAIL pure_vertical_scan_20"); ++errors; }
 /* pure_vertical_scan_21 */
 valid=ai_v6_prepare_window(21u,UINT64_C(840),21u,1u,1u,21u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1501017f1402)){ puts("FAIL pure_vertical_scan_21"); ++errors; }
 /* pure_vertical_scan_22 */
 valid=ai_v6_prepare_window(22u,UINT64_C(880),22u,1u,1u,22u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1601017f1402)){ puts("FAIL pure_vertical_scan_22"); ++errors; }
 /* pure_vertical_scan_23 */
 valid=ai_v6_prepare_window(23u,UINT64_C(920),23u,1u,1u,23u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1701017f1402)){ puts("FAIL pure_vertical_scan_23"); ++errors; }
 /* pure_vertical_scan_24 */
 valid=ai_v6_prepare_window(24u,UINT64_C(960),24u,1u,1u,24u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1801017f1403)){ puts("FAIL pure_vertical_scan_24"); ++errors; }
 /* pure_vertical_scan_25 */
 valid=ai_v6_prepare_window(25u,UINT64_C(1000),25u,1u,1u,25u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1901017f1403)){ puts("FAIL pure_vertical_scan_25"); ++errors; }
 /* pure_vertical_scan_26 */
 valid=ai_v6_prepare_window(26u,UINT64_C(1040),26u,1u,1u,26u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1a01017f1403)){ puts("FAIL pure_vertical_scan_26"); ++errors; }
 /* pure_vertical_scan_27 */
 valid=ai_v6_prepare_window(27u,UINT64_C(1080),27u,1u,1u,27u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1b01017f1403)){ puts("FAIL pure_vertical_scan_27"); ++errors; }
 /* pure_vertical_scan_28 */
 valid=ai_v6_prepare_window(28u,UINT64_C(1120),28u,1u,1u,28u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1c01017f1403)){ puts("FAIL pure_vertical_scan_28"); ++errors; }
 /* pure_vertical_scan_29 */
 valid=ai_v6_prepare_window(29u,UINT64_C(1160),29u,1u,1u,29u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1d01017f1403)){ puts("FAIL pure_vertical_scan_29"); ++errors; }
 /* pure_vertical_scan_30 */
 valid=ai_v6_prepare_window(30u,UINT64_C(1200),30u,1u,1u,30u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x1e01017f1403)){ puts("FAIL pure_vertical_scan_30"); ++errors; }
 /* syn_flood_sensor_407 */
 valid=ai_v6_prepare_window(407u,UINT64_C(16427),401u,2u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0101027d1432)){ puts("FAIL syn_flood_sensor_407"); ++errors; }
 /* syn_low_sensor_26 */
 valid=ai_v6_prepare_window(26u,UINT64_C(1044),26u,2u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0101027f1403)){ puts("FAIL syn_low_sensor_26"); ++errors; }
 /* syn_high_sensor_2007 */
 valid=ai_v6_prepare_window(2007u,UINT64_C(80427),2001u,2u,1u,1u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x0101027e147f)){ puts("FAIL syn_high_sensor_2007"); ++errors; }
 /* vertical_scan_sensor_257 */
 valid=ai_v6_prepare_window(257u,UINT64_C(11427),251u,2u,1u,251u,&feat);
 if(valid!=1 || feat!=UINT64_C(0x7f01027c1620)){ puts("FAIL vertical_scan_sensor_257"); ++errors; }
 if(!errors) puts("PASS C_PACK cases=41 valid=40 empty_skipped=1");
 return errors ? 1 : 0;
}
