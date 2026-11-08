#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -eq 0 ] || { echo 'Use sudo bash lab/collect_challenge.sh [unique_prefix]';exit 1; }
PREFIX="${1:-challenge_$(date +%Y%m%d_%H%M%S)}"
[[ "$PREFIX" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid prefix';exit 1; }
[ -f build/lab.created ] || { echo 'Create the isolated lab first';exit 1; }
for ns in p2broker p2sensor p2source; do
 ip netns exec "$ns" ip link show eth0 >/dev/null || { echo 'Lab is missing: use setup_lab.sh down/up';exit 1; }
done
# New conditions, same frozen v1. No training and no changes to original captures/manifest.
bash lab/run_capture.sh normal challenge "${PREFIX}_normal_large" 30 200 0.5 1 512
bash lab/run_capture.sh normal challenge "${PREFIX}_normal_two" 30 200 0.2 2 1024
bash lab/run_capture.sh normal_probe challenge "${PREFIX}_normal_retry" 30 8 1 1
bash lab/run_capture.sh syn challenge "${PREFIX}_syn_low" 30 20
bash lab/run_capture.sh syn challenge "${PREFIX}_syn_high" 30 400
bash lab/run_capture.sh scan challenge "${PREFIX}_scan_slow" 30 5
bash lab/run_capture.sh scan challenge "${PREFIX}_scan_fast" 30 300
echo 'Challenge captures saved separately under data/challenge. Do not retrain v1 on them.'
