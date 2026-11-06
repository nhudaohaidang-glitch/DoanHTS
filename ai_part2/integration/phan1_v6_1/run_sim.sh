#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
exec python3 tools/run_sim.py "${1:-full}"
