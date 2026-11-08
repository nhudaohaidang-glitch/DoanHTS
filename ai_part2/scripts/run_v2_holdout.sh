#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -ne 0 ] || { echo 'Run without sudo';exit 1; }
PREFIX="${1:?Usage: bash scripts/run_v2_holdout.sh PREFIX [MODEL_DIR]}"
[[ "$PREFIX" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid prefix';exit 1; }
MODEL_DIR="${2:-build/lab_model_v2}"
DATA="data/v2_holdout/$PREFIX"
FEATURES="build/v2_holdout_$PREFIX.csv"
OUT="build/v2_holdout_eval_$PREFIX"
[ -f "$DATA/COMPLETE.json" ] || { echo 'Holdout collection incomplete; inspect capture logs first';exit 1; }
[ ! -e "$FEATURES" ] && [ ! -e "$OUT" ] || { echo 'Output exists; preserve this result';exit 1; }
.venv/bin/python tools/feature_quant.py --manifest "$DATA/manifest.csv" --output "$FEATURES" > "build/v2_holdout_$PREFIX.log"
.venv/bin/python tools/evaluate_v2.py --dataset "$FEATURES" --model-dir "$MODEL_DIR" --collection-record "$DATA/COLLECTION.json" --output "$OUT"
echo "Open with Firefox: $OUT/report.html"
