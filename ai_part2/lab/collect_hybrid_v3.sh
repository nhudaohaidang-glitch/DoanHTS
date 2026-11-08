#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="${1:?Usage: sudo bash lab/collect_hybrid_v3.sh PREFIX [--resume]}"
shift
exec .venv/bin/python lab/collect_v2.py holdout "$PREFIX" --profile hybrid-v3 --model-dir gowin/hybrid_v3/model "$@"
