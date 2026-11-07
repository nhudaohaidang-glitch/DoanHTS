# =============================================================================
# modelsim_demo.do - Chay cac demo bang ModelSim / Questa (khong can Icarus)
#
# Cach chay:
#   1. ModelSim: File > Change Directory -> thu muc goc du an (co file sources.f)
#   2. O cua so Transcript go MOT trong cac lenh:
#        do sim/modelsim_demo.do quick    9 giay dau, CO dang song (giong modelsim_gateway.do)
#        do sim/modelsim_demo.do full     ca kich ban 40 giay + kiem log bang Python
#        do sim/modelsim_demo.do oled     man OLED (mo hinh SSD1306, in chu ra Transcript)
#        do sim/modelsim_demo.do board    top cua kit voi firmware.hex that
#        do sim/modelsim_demo.do mac      rieng MAC Ethernet Phan 4 (nhanh nhat)
#        do sim/modelsim_demo.do system   toan he thong voi MAC that
#   Khong ghi ten = quick.
#
# Ket qua [tb] OK / LOI / PASS hien o Transcript; log UART ghi them vao sim/out/.
# Lan dau bien dich mat ~1 phut. "full" va "oled" chay lau (chay san truoc gio kiem tra).
# =============================================================================
if {![file exists sources.f]} {
    error "Hay File > Change Directory toi thu muc goc du an (co file sources.f) truoc"
}
if {$argc > 0} { set ten $1 } else { set ten quick }
if {$ten eq "quick"} {
    do sim/modelsim_gateway.do
} else {
    do sim/modelsim_run.do $ten
}
