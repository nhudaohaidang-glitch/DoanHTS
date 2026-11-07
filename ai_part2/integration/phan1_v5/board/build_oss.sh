#!/usr/bin/env sh
# =============================================================================
# Dung file nap .fs cho Tang Nano 9K bang bo cong cu ma nguon mo
# (Yosys + nextpnr-himbaechel + apicula). Chay tu bat ky dau:
#   ./board/build_oss.sh          ban tu thu: khoi gia eth_stub tu tao luu luong (SELFTEST = 1)
#   ./board/build_oss.sh noeth    ban kiem tra noi day: cong Ethernet nghi (SELFTEST = 0)
# Can: pip install yowasp-yosys yowasp-nextpnr-himbaechel-gowin apycula
# (hoac ban cai san: YOSYS=yosys NEXTPNR=nextpnr-himbaechel ./board/build_oss.sh)
# Luu y: nextpnr chi kiem thoi gian clock 27 MHz; 2 clock REF_CLK 50 MHz hien chi vao bo do
# tan so (clk_meter). Khi Phan 4 them MAC RMII, kiem them 2 clock nay bang Gowin (file .sdc).
# =============================================================================
set -e
cd "$(dirname "$0")/.."
YOSYS=${YOSYS:-yowasp-yosys}
NEXTPNR=${NEXTPNR:-yowasp-nextpnr-himbaechel-gowin}
mkdir -p build
[ -f fw/firmware.hex ] || (cd fw && ./build_fw.sh)

SRC="$(grep -v '^#' sources.f | tr '\n' ' ') rtl/board/tangnano9k_top.v"
if [ "$1" = "noeth" ]; then NAME=tangnano9k_noeth; SELFTEST=0; else NAME=tangnano9k; SELFTEST=1; fi

echo "== Tong hop (Yosys)"
$YOSYS -q -l build/yosys.log \
    -p "read_verilog $SRC; chparam -set SELFTEST $SELFTEST tangnano9k_top; synth_gowin -top tangnano9k_top -json build/${NAME}_synth.json"

echo "== Dat va di day (nextpnr)"
$NEXTPNR -q -l build/${NAME}_nextpnr.log \
    --json build/${NAME}_synth.json --write build/${NAME}_pnr.json \
    --device GW1NR-LV9QN88PC6/I5 --vopt family=GW1N-9C \
    --vopt cst=board/tangnano9k.cst --freq 27

echo "== Dong goi file nap (apicula)"
gowin_pack -d GW1N-9C -o build/${NAME}.fs build/${NAME}_pnr.json

sed -n '/Device utilisation/,/^$/p' build/${NAME}_nextpnr.log | grep -E "IOB|LUT4|ALU:|DFF|BSRAM|MULT9|RAM16SDP4"
grep -E "Max frequency for clock" build/${NAME}_nextpnr.log | tail -3
echo "OK: build/${NAME}.fs"
