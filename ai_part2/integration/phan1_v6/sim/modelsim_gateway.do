# =============================================================================
# modelsim_gateway.do - Mo phong toan he thong (tuong lua Ethernet) bang ModelSim / Questa
# Cach chay: File > Change Directory -> thu muc goc du an (co file sources.f),
#            roi go o cua so Transcript:   do sim/modelsim_gateway.do
# Mac dinh chay 9 "giay" mo phong (~50 ms thoi gian mo phong, vai phut) - du thay:
# cua so rong, cam bien, SYN flood tu .50 va lan chan dau tien.
# Muon chay ca kich ban 40 giay + tu kiem tra: sua dong vsim, bo "+stop=9".
#
# Chay xong, go them o Transcript de nhay toi doan can xem:
#   xem_khung     khung dau tien cua cam bien: byte di vao, ban ghi header, verdict cho qua
#   xem_uart      1 byte log tren chan uart_txd
#   xem_ai        cua so 2: CPU nap dac trung, ai_start -> ai_done (84 chu ky), doc ket qua
#   xem_chan      cua so 6 (SYN flood lan 2 lien tiep): CPU ghi IP .50 vao danh sach chan,
#                 bl_valid len 1, khung tiep theo cua .50 bi bo (verdict_drop = 1)
#   xem_het       thu toan bo
# Log UART dong thoi hien o Transcript va ghi vao sim/out/uart.log
# =============================================================================
if {![file exists sources.f]} {
    error "Hay File > Change Directory toi thu muc goc du an (co file sources.f) truoc"
}
file mkdir sim/out
if {[file exists work]} { vdel -lib work -all }
vlib work

set files {}
set fh [open sources.f r]
foreach line [split [read $fh] "\n"] {
    set line [string trim $line]
    if {$line ne "" && [string index $line 0] ne "#"} { lappend files $line }
}
close $fh
eval vlog -sv -timescale 1ns/1ps $files sim/tb_gateway.v

vsim -voptargs=+acc -onfinish stop +stop=9 work.tb_gateway

set T /tb_gateway
set S /tb_gateway/dut
add wave -divider "Thoi gian"
add wave -label clk          $T/clk
add wave -label giay         -radix unsigned $T/u_eth/phase
add wave -divider "Phan 4 (khoi gia) -> Phan 3: dong byte khung"
add wave -label frm_valid    $T/frm_valid
add wave -label frm_sof      $T/frm_sof
add wave -label frm_eof      $T/frm_eof
add wave -label frm_data     -radix hex $T/frm_data
add wave -divider "Phan 3: ban ghi header"
add wave -label hdr_valid    $S/h_valid
add wave -label src_ip       -radix hex $S/h_src
add wave -label tcp_flags    -radix hex $S/h_flags
add wave -divider "Phan 3: bo loc -> Phan 4"
add wave -label bl_en        $S/bl_en
add wave -label bl_valid     -radix bin $S/bl_valid
add wave -label verdict_valid $T/verdict_valid
add wave -label verdict_drop $T/verdict_drop
add wave -divider "Phan 3: dac trung (moi cua so)"
add wave -label win_valid    $S/f_valid
add wave -label win_id       -radix unsigned $S/f_win_id
add wave -label pkt_cnt      -radix unsigned $S/f_pkt
add wave -label suspect_ip   -radix hex $S/f_susp
add wave -label confirm_cnt  -radix unsigned $S/f_conf
add wave -divider "CPU - bus Wishbone"
add wave -label wb_stb       $S/wb_stb
add wave -label wb_we        $S/wb_we
add wave -label wb_ack       $S/wb_ack
add wave -label wb_adr       -radix hex $S/wb_adr
add wave -label wb_dat_w     -radix hex $S/wb_dat_w
add wave -label wb_dat_r     -radix hex $S/wb_dat_r
add wave -divider "Phan 2: AI V6"
add wave -label ai_start     $S/a_start
add wave -label ai_busy      $S/a_busy
add wave -label ai_done      $S/a_done
add wave -label ai_class     -radix unsigned $S/a_class
add wave -label ai_feat      -radix hex $S/a_feat
add wave -divider "Log"
add wave -label uart_txd     $T/uart_txd
configure wave -signalnamewidth 1

# moc thoi gian do tren Icarus voi cung testbench (1 giay mo phong = 150 000 chu ky = 5,555 ms)
proc xem_khung {} { wave zoom range 11805000ns 11815000ns }
proc xem_uart  {} { wave zoom range 17548000ns 17557000ns }
proc xem_ai    {} { wave zoom range 18620000ns 18632000ns }
proc xem_chan  {} { wave zoom range 39275000ns 39300000ns }
proc xem_het   {} { wave zoom full }

run -all
xem_chan
