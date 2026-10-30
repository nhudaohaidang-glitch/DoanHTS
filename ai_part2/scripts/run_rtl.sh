#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KIT_DIR="$PWD"
MODEL_DIR="$(realpath "${1:-build/demo_model}")"
for f in w1.hex w2.hex b1.hex b2.hex quant_params.vh vectors.txt; do test -s "$MODEL_DIR/$f"; done
iverilog -g2012 -Wall -s tb_ai_core -I "$MODEL_DIR" -o "$MODEL_DIR/sim.vvp" rtl/ai_core.v sim/tb_ai_core.v
cd "$MODEL_DIR"
vvp sim.vvp | tee rtl_result.log
grep -q '^PASS vectors=' rtl_result.log
