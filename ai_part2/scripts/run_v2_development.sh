#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -ne 0 ] || { echo 'Run without sudo';exit 1; }
PREFIX="${1:?Usage: bash scripts/run_v2_development.sh PREFIX [MODEL_DIR]}"
[[ "$PREFIX" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid prefix';exit 1; }
MODEL_DIR="${2:-build/lab_model_v2}"
DATA="data/v2_development/$PREFIX"
FEATURES="build/v2_features_$PREFIX.csv"
[ -f "$DATA/COMPLETE.json" ] || { echo 'Collection is incomplete; inspect capture logs first';exit 1; }
[ ! -e "$FEATURES" ] && [ ! -e "$MODEL_DIR" ] || { echo 'Output exists; preserve it and choose a new prefix/model directory';exit 1; }
command -v iverilog >/dev/null && command -v vvp >/dev/null || { echo 'Install iverilog using the existing Ubuntu installer first';exit 1; }
.venv/bin/python tools/feature_quant.py --manifest "$DATA/manifest.csv" --output "$FEATURES" > "build/v2_features_$PREFIX.log"
.venv/bin/python tools/train_v2.py --dataset "$FEATURES" --output "$MODEL_DIR" > "build/v2_training_$PREFIX.log"
bash scripts/run_rtl.sh "$MODEL_DIR"
.venv/bin/python - "$MODEL_DIR" <<'PY'
import json,sys
from pathlib import Path
report=json.loads((Path(sys.argv[1])/'metrics.json').read_text())
print('VALIDATION ONLY - NOT A FINAL TEST:')
for kind in ('float','integer'):
    m=report['metrics']['val'][kind]
    print(kind, 'accuracy=',m['accuracy'],'macro-F1=',m['macro_f1'],'FPR=',m['false_positive_rate'])
    print('confusion_matrix=',m['confusion_matrix'])
print('Convergence warnings:',report['convergence_warning_count'])
print('Saved separate candidate:',sys.argv[1])
print('Send validation results before collecting the final holdout.')
PY
