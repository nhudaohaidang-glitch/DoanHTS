# modelsim_run.do - phan than cua modelsim_demo.do (dung goi truc tiep: do sim/modelsim_demo.do <ten>)
set ten $1
file mkdir sim/out
if {[file exists work]} { vdel -lib work -all }
vlib work

# ---- bien dich: toan bo RTL + top cua kit + moi testbench (ten module khong trung nhau)
set files {}
set fh [open sources.f r]
foreach line [split [read $fh] "\n"] {
    set line [string trim $line]
    if {$line ne "" && [string index $line 0] ne "#"} { lappend files $line }
}
close $fh
lappend files rtl/board/tangnano9k_top.v sim/ssd1306_model.v \
    sim/tb_gateway.v sim/tb_oled.v sim/tb_board.v sim/tb_eth_mac.v sim/tb_system_mac.v
eval vlog -sv -timescale 1ns/1ps $files

# ---- chon testbench
switch -- $ten {
    full    { set top tb_gateway }
    oled    { set top tb_oled }
    board   { set top tb_board }
    mac     { set top tb_eth_mac }
    system  { set top tb_system_mac }
    default { error "Ten demo khong dung: $ten (quick, full, oled, board, mac, system)" }
}

# -onfinish stop: chay xong khong dong ModelSim, van xem duoc ket qua
vsim -voptargs=+acc -onfinish stop work.$top

# dang song toi thieu cho bai MAC va bai he thong (bai khac xem log la du)
if {$ten eq "mac"} {
    add wave -divider "Cong A (vao)"
    add wave -label a_crs_dv /tb_eth_mac/a_crs
    add wave -label a_rxd    -radix bin /tb_eth_mac/a_rxd
    add wave -divider "MAC -> he thong (27 MHz)"
    add wave -label frm_valid /tb_eth_mac/fv
    add wave -label frm_data  -radix hex /tb_eth_mac/fdata
    add wave -label frm_eof   /tb_eth_mac/feof
    add wave -label crc_ok    /tb_eth_mac/fok
    add wave -label verdict_drop /tb_eth_mac/vd
    add wave -divider "Cong B (ra)"
    add wave -label b_tx_en  /tb_eth_mac/b_txen
    add wave -label b_txd    -radix bin /tb_eth_mac/b_txd
    add wave -label mac_crc_err /tb_eth_mac/crc_err
}
if {$ten eq "system"} {
    set S /tb_system_mac/dut/u_soc
    add wave -label a_crs_dv /tb_system_mac/a_crs
    add wave -label frm_valid $S/frm_valid
    add wave -label frm_data  -radix hex $S/frm_data
    add wave -label hdr_valid $S/h_valid
    add wave -label src_ip    -radix hex $S/h_src
    add wave -label win_valid $S/f_valid
    add wave -label ai_start  $S/a_start
    add wave -label ai_class  -radix unsigned $S/a_class
    add wave -label bl_valid  -radix bin $S/bl_valid
    add wave -label verdict_drop $S/verdict_drop
    add wave -label b_tx_en   /tb_system_mac/b_txen
}
configure wave -signalnamewidth 1

run -all
if {$ten eq "mac" || $ten eq "system"} { wave zoom full }

# ---- bai full: kiem log UART bang Python (neu co Python trong PATH)
if {$ten eq "full"} {
    foreach py {python python3 py} {
        if {![catch {exec $py tools/check_log.py sim/out/uart.log} out]} {
            echo $out; break
        } elseif {[string match "*PASS*" $out] || [string match "*FAIL*" $out]} {
            echo $out; break
        }
    }
}
