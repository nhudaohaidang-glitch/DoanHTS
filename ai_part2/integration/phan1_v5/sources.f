# Danh sach file RTL (thu tu bien dich) - Phan 1 phien ban tuong lua Ethernet
# Khi ghep phan cua nhom, thay KHOI GIA bang khoi that, giu nguyen ten module va cong:
#   rtl/stubs/pkt_parser_stub.v -> pkt_parser.v (Phan 3)
#   rtl/stubs/feat_core_stub.v  -> feat_core.v  (Phan 3)
#   rtl/stubs/pkt_filter_stub.v -> pkt_filter.v (Phan 3)
# Phan 2 (AI v5) da la khoi that:  rtl/part2_ai/ai_core_model_v5.v (khong sua)
# Phan 4 (MAC Ethernet that):      rtl/part4_eth/*.v
#   - Dung o top cua kit khi SELFTEST = 2 (thay eth_stub).
#   - eth_stub chi con dung cho mo phong / demo (SELFTEST = 1).
rtl/picorv32.v
rtl/fw_ram.v
rtl/uart_tx.v
rtl/wb_ram.v
rtl/wb_uart.v
rtl/clk_meter.v
rtl/wb_sys.v
rtl/wb_feat_regs.v
rtl/wb_ai_regs.v
rtl/wb_filter_regs.v
rtl/gateway_soc.v
rtl/part2_ai/ai_core_model_v5.v
rtl/stubs/pkt_parser_stub.v
rtl/stubs/feat_core_stub.v
rtl/stubs/pkt_filter_stub.v
rtl/part4_eth/async_fifo.v
rtl/part4_eth/rmii_rx.v
rtl/part4_eth/rmii_tx.v
rtl/part4_eth/eth_mac.v
rtl/stubs/eth_stub.v
