// Rang buoc thoi gian: clock he thong 27 MHz + 2 clock RMII 50 MHz tu 2 module LAN8720.
// Ba clock khong lien quan nhau: moi tin hieu qua lai giua chung phai di qua FIFO bat dong bo.
create_clock -name clk_27m   -period 37.037 -waveform {0 18.518} [get_ports {clk_27m}]
create_clock -name a_ref_clk -period 20     -waveform {0 10}     [get_ports {a_ref_clk}]
create_clock -name b_ref_clk -period 20     -waveform {0 10}     [get_ports {b_ref_clk}]
set_clock_groups -asynchronous -group [get_clocks {clk_27m}] -group [get_clocks {a_ref_clk}] -group [get_clocks {b_ref_clk}]
