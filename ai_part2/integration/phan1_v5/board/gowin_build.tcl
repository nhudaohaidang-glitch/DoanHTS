# =============================================================================
# gowin_build.tcl - Dung file nap bang Gowin EDA o che do dong lenh (gw_sh)
# Chay tu thu muc goc gateway_v2 (Command Prompt):
#     "C:\Gowin\Gowin_V1.9.x_x64\IDE\bin\gw_sh.exe" board\gowin_build.tcl
# (sua duong dan gw_sh.exe theo noi ban cai Gowin)
# - Doc danh sach file RTL tu sources.f (giong mo phong)
# - Tu tao build/gowin/gowin_top.v chua duong dan TUYET DOI toi fw/firmware.hex
#   de Gowin luon tim thay file khoi tao RAM
# - Dung board/tangnano9k.sdc: 3 clock (27 MHz + 2 x 50 MHz REF_CLK), khong lien quan nhau
# Ket qua: impl/pnr/tangnano9k.fs
# =============================================================================
# selftest: 2 = MAC Ethernet that (Phan 4)   <- dung de KIEM TRA CO VUA KIT KHONG
#           1 = khoi gia eth_stub tu tao luu luong (demo khong can laptop)
#           0 = ban kiem tra noi day (cong Ethernet nghi)
# ref_meter: 1 = giu bo do REF_CLK (can khi kiem tra day), 0 = bo de tiet kiem ~370 o logic
set selftest  2
set ref_meter 0

set root [file normalize [file join [file dirname [info script]] ..]]
cd $root
set fw [file normalize [file join $root fw firmware.hex]]
if {![file exists $fw]} { error "Khong thay $fw - hay bien dich firmware truoc (fw/build_fw.sh)" }

file mkdir [file join $root build gowin]
set wrap [file join $root build gowin gowin_top.v]
set f [open $wrap w]
puts $f "// Tu sinh boi gowin_build.tcl - khong sua tay"
puts $f "module gowin_top ("
puts $f "    input clk_27m, input rst_n, input key_n, output uart_tx,"
puts $f "    inout oled_sda, inout oled_scl,"
puts $f "    input a_ref_clk, input a_crs_dv, input \[1:0\] a_rxd, output a_tx_en, output \[1:0\] a_txd,"
puts $f "    input b_ref_clk, input b_crs_dv, input \[1:0\] b_rxd, output b_tx_en, output \[1:0\] b_txd,"
puts $f "    output \[5:0\] led_n);"
puts $f "    tangnano9k_top #(.FIRMWARE(\"$fw\"), .SELFTEST($selftest), .REF_METER($ref_meter)) u_top ("
puts $f "        .clk_27m(clk_27m), .rst_n(rst_n), .key_n(key_n), .uart_tx(uart_tx),"
puts $f "        .oled_sda(oled_sda), .oled_scl(oled_scl),"
puts $f "        .a_ref_clk(a_ref_clk), .a_crs_dv(a_crs_dv), .a_rxd(a_rxd), .a_tx_en(a_tx_en), .a_txd(a_txd),"
puts $f "        .b_ref_clk(b_ref_clk), .b_crs_dv(b_crs_dv), .b_rxd(b_rxd), .b_tx_en(b_tx_en), .b_txd(b_txd),"
puts $f "        .led_n(led_n));"
puts $f "endmodule"
close $f

set_device GW1NR-LV9QN88PC6/I5 -device_version C

set src [open [file join $root sources.f] r]
foreach line [split [read $src] "\n"] {
    set line [string trim $line]
    if {$line eq "" || [string index $line 0] eq "#"} { continue }
    add_file $line
}
close $src
add_file rtl/board/tangnano9k_top.v
add_file build/gowin/gowin_top.v
add_file board/tangnano9k.cst
add_file board/tangnano9k.sdc

set_option -top_module gowin_top
set_option -verilog_std sysv2017
set_option -output_base_name tangnano9k
# Neu Gowin bao chan trung chuc nang phu (MSPI/SSPI/JTAG/READY/DONE/RECONFIG_N), bat dung
# muc trong Project > Configuration > Dual-Purpose Pin, hoac them dong set_option tuong ung.

run all
