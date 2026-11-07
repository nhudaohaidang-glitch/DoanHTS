#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p verification/build
iverilog -g2012 -Wall -s tb_ai_core -o verification/build/sim.vvp src/ai_core_model_v1.v verification/tb_ai_core.v
vvp verification/build/sim.vvp +vectors=verification/vectors.txt | tee verification/build/result.log
grep -q '^PASS vectors=' verification/build/result.log
