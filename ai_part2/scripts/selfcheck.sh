#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PART2_PYTHON:-$PWD/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then echo 'Install first, or set PART2_PYTHON to a configured interpreter.' >&2; exit 1; fi
"$PYTHON" -m unittest discover -s tests -v
if [ -e build/demo_data ] || [ -e build/demo_model ]; then
  echo 'Demo outputs already exist; preserve or rename them before a fresh selfcheck.' >&2; exit 1
fi
"$PYTHON" tools/make_synthetic_demo.py --output build/demo_data
"$PYTHON" tools/feature_quant.py --manifest build/demo_data/manifest.csv --output build/demo_features.csv
"$PYTHON" tools/train.py --dataset build/demo_features.csv --output build/demo_model --allow-synthetic > build/demo_training.log
bash scripts/run_rtl.sh build/demo_model
printf '\nSelfcheck finished. Synthetic data: NOT evidence of real attack accuracy.\n'
