#!/usr/bin/env sh
# Bien dich firmware (Linux/WSL/Git Bash). Tao 2 file:
#   firmware.hex      ban nap kit (thoi gian that: chan 60 s, I2C ~100 kHz)
#   firmware_sim.hex  ban mo phong (-DSIM_FAST: chan 6 "giay", I2C khong cho)
# Doi PREFIX neu dung bo bien dich khac, vi du:  PREFIX=riscv-none-elf- ./build_fw.sh
set -e
cd "$(dirname "$0")"
PREFIX=${PREFIX:-riscv64-unknown-elf-}
CFLAGS="-march=rv32i -mabi=ilp32 -Os -ffreestanding -fno-builtin -nostdlib -Wall -Wextra -I. $EXTRA_CFLAGS"
SRC="start.S main.c oled.c font5x7.c uart.c libc_min.c"

build() {   # $1 = ten, $2 = co them
    ${PREFIX}gcc $CFLAGS $2 -T link.ld -Wl,-Map,$1.map,--no-warn-rwx-segments,--gc-sections \
        -ffunction-sections -fdata-sections $SRC -lgcc -o $1.elf
    ${PREFIX}objcopy -O binary $1.elf $1.bin
    ${PREFIX}objdump -d $1.elf > $1.lst
    ${PREFIX}size $1.elf
    python3 makehex.py $1.bin 4096 > $1.hex
}
build firmware ""
build firmware_sim "-DSIM_FAST"
echo "OK: fw/firmware.hex, fw/firmware_sim.hex (RAM 16 KB = 16384 byte, gom ca ngan xep)"
