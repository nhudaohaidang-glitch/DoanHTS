#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -ne 0 ] || { echo 'Run without sudo';exit 1; }
PREFIX="${1:?Usage: bash scripts/run_hybrid_v3_holdout.sh PREFIX}"
[[ "$PREFIX" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid prefix';exit 1; }
DATA="data/v3_holdout/$PREFIX"
FEATURES="build/hybrid_v3_holdout_$PREFIX.csv"
OUT="build/hybrid_v3_eval_$PREFIX"
[ -f "$DATA/COMPLETE.json" ] || { echo 'Fresh lab collection incomplete';exit 1; }
[ ! -e "$FEATURES" ] && [ ! -e "$OUT" ] || { echo 'Output exists; preserve previous result';exit 1; }
.venv/bin/python tools/feature_quant.py --manifest "$DATA/manifest.csv" --output "$FEATURES" > "build/hybrid_v3_holdout_$PREFIX.log"
.venv/bin/python tools/evaluate_hybrid_v3.py --lab-dataset "$FEATURES" --collection-record "$DATA/COLLECTION.json" --output "$OUT"
echo "Open in Ubuntu Firefox: $OUT/report.html"
