#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KIT_DIR="$PWD"
[ "$(id -u)" -eq 0 ] || { echo 'Use sudo bash lab/run_capture.sh MODE SPLIT ID [SECONDS]';exit 1; }
MODE="${1:-}";SPLIT="${2:-}";RUN_ID="${3:-}";SECONDS_RUN="${4:-20}"
PPS="${5:-200}";SENSOR_INTERVAL="${6:-1}";NORMAL_CLIENTS="${7:-1}";PAYLOAD_BYTES="${8:-0}"
CAPTURE_SET="${9:-}"
case "$MODE" in normal|normal_probe) LABEL=0;;syn) LABEL=1;;scan) LABEL=2;;*) echo 'MODE normal|normal_probe|syn|scan';exit 1;;esac
case "$NORMAL_CLIENTS" in 1|2);;*) echo "NORMAL_CLIENTS must be 1 or 2";exit 1;;esac
case "$SPLIT" in train|val|test|challenge);;*) echo 'SPLIT train|val|test|challenge';exit 1;;esac
[[ "$RUN_ID" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid run ID';exit 1; }
[[ "$SECONDS_RUN" =~ ^[0-9]+$ ]] && [ "$SECONDS_RUN" -ge 10 ] && [ "$SECONDS_RUN" -le 60 ] || { echo 'Duration must be 10..60 seconds';exit 1; }
[ -f build/lab.created ] || { echo 'Run setup_lab.sh up first';exit 1; }
PYTHON="$KIT_DIR/.venv/bin/python"
[ -x "$PYTHON" ] || { echo 'Run install_ubuntu.sh first';exit 1; }
"$PYTHON" -c 'import sys; assert 1<=int(sys.argv[1])<=500 and 0.2<=float(sys.argv[2])<=5, "pps 1..500, sensor interval 0.2..5"' "$PPS" "$SENSOR_INTERVAL"
SEED="$("$PYTHON" -c 'import hashlib,sys;print(int(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:8],16))' "$RUN_ID")"
CAPTURE_ROOT="$KIT_DIR/data/captures"
if [ "$SPLIT" = challenge ]; then CAPTURE_ROOT="$KIT_DIR/data/challenge"; fi
if [ -n "$CAPTURE_SET" ]; then
 [[ "$CAPTURE_SET" =~ ^v2_(development|holdout)/[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid v2 capture set';exit 1; }
 case "$CAPTURE_SET:$SPLIT" in
  v2_development/*:train|v2_development/*:val|v2_holdout/*:challenge);;
  *) echo 'v2 development requires train/val; holdout requires challenge';exit 1;;
 esac
 CAPTURE_ROOT="$KIT_DIR/data/$CAPTURE_SET"
fi
OUT="$CAPTURE_ROOT/$RUN_ID"
[ ! -e "$OUT" ] || { echo 'Run directory exists; refusing overwrite';exit 1; }
"$PYTHON" -c 'import sys;assert 0<=int(sys.argv[1])<=4096' "$PAYLOAD_BYTES"
if [ "$MODE" = normal_probe ] && [ "$PPS" -gt 10 ]; then echo 'normal_probe limited to 10 attempts/s';exit 1;fi
mkdir -p "$OUT"
printf 'mode=%s\nsplit=%s\nrequested_pps=%s\nsensor_interval=%s\nseed=%s\n' "$MODE" "$SPLIT" "$PPS" "$SENSOR_INTERVAL" "$SEED" > "$OUT/scenario.txt"
printf 'normal_clients=%s\nseconds=%s\npayload_bytes=%s\n' "$NORMAL_CLIENTS" "$SECONDS_RUN" "$PAYLOAD_BYTES" >> "$OUT/scenario.txt"
# Runtime config lives under Mosquitto's standard configuration tree so Ubuntu
# confinement need not allow arbitrary files under a user's home directory.
# This subdirectory is not conf.d and is not included by the normal service.
BROKER_CONFIG=""
PIDS=()
EXTRA_SENSOR_PID=""
cleanup() {
 for pid in "${PIDS[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
 for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
 if [ -n "$BROKER_CONFIG" ]; then rm -f -- "$BROKER_CONFIG"; BROKER_CONFIG=""; fi
 if [ -n "${SUDO_UID:-}" ]; then chown -R "$SUDO_UID:${SUDO_GID:-$SUDO_UID}" "$OUT"; fi
}
trap cleanup EXIT
mkdir -p /etc/mosquitto/part2-lab
BROKER_CONFIG="$(mktemp /etc/mosquitto/part2-lab/session.XXXXXXXX.conf)"
cat > "$BROKER_CONFIG" <<'EOF'
listener 1883 198.18.0.1
allow_anonymous true
persistence false
max_connections 30
EOF
chmod 644 "$BROKER_CONFIG"
cat "$BROKER_CONFIG" > "$OUT/mosquitto.conf"
ip netns exec p2broker mosquitto -c "$BROKER_CONFIG" > "$OUT/broker.log" 2>&1 & PIDS+=("$!")
sleep 0.5
kill -0 "${PIDS[0]}" || { cat "$OUT/broker.log";exit 1; }
ip netns exec p2broker "$PYTHON" -u lab/broker_observer.py > "$OUT/received.jsonl" 2>&1 & PIDS+=("$!")
ip netns exec p2broker tcpdump -U -n -i eth0 -s 0 -w - > "$OUT/traffic.pcap" 2> "$OUT/capture.log" & PIDS+=("$!")
sleep 0.5
kill -0 "${PIDS[2]}" || { cat "$OUT/capture.log";exit 1; }
ip netns exec p2broker "$PYTHON" -u lab/broker_stats.py --seconds "$SECONDS_RUN" > "$OUT/broker_stats.jsonl" 2>&1 & PIDS+=("$!")
SENSOR_COUNT="$("$PYTHON" -c 'import math,sys;print(math.ceil(int(sys.argv[1])/float(sys.argv[2])))' "$SECONDS_RUN" "$SENSOR_INTERVAL")"
ip netns exec p2sensor "$PYTHON" -u lab/sensor_client.py --count "$SENSOR_COUNT" --interval "$SENSOR_INTERVAL" --client-prefix p2-primary --payload-bytes "$PAYLOAD_BYTES" > "$OUT/sensor.jsonl" 2>&1 & PIDS+=("$!")
if [ "$MODE" = normal ] && [ "$NORMAL_CLIENTS" -eq 2 ]; then
 ip netns exec p2source "$PYTHON" -u lab/sensor_client.py --count "$SENSOR_COUNT" --interval "$SENSOR_INTERVAL" --client-prefix p2-secondary --payload-bytes "$PAYLOAD_BYTES" > "$OUT/sensor_extra.jsonl" 2>&1 &
 EXTRA_SENSOR_PID="$!";PIDS+=("$EXTRA_SENSOR_PID")
fi
START="$(date +%s.%N)"
if [ "$MODE" != normal ]; then
 ip netns exec p2source "$PYTHON" -u lab/lab_traffic.py --mode "${MODE/normal_probe/probe}" --seconds "$SECONDS_RUN" --pps "$PPS" --seed "$SEED" > "$OUT/source.log" 2>&1 &
 PIDS+=("$!")
fi
sleep "$SECONDS_RUN"
END="$(date +%s.%N)"
# Check services that must stay alive; exit without registering incomplete captures on failure.
kill -0 "${PIDS[0]}";kill -0 "${PIDS[1]}";kill -0 "${PIDS[2]}"
cleanup
PIDS=()
if [ "$MODE" != normal ]; then
 grep -Eq '^mode=((syn|scan) packets|probe attempts)=[1-9][0-9]* ' "$OUT/source.log" || { echo 'Source did not complete with packets; inspect source.log. Capture NOT registered.'; exit 1; }
fi
# Exclude startup/stop boundary windows; retain absolute timestamps for reproducibility.
START="$("$PYTHON" -c 'import sys;print(float(sys.argv[1])+2)' "$START")"
END="$("$PYTHON" -c 'import sys;print(float(sys.argv[1])-1)' "$END")"
# A two-source normal control is valid only if both clients sent successfully.
if [ "$MODE" = normal ] && [ "$NORMAL_CLIENTS" -eq 2 ]; then
 "$PYTHON" - "$OUT" <<'PY_CHECK'
import json,sys
from pathlib import Path
for name in ('sensor.jsonl','sensor_extra.jsonl'):
    with (Path(sys.argv[1])/name).open() as f:
        rows=[json.loads(line) for line in f if line.lstrip().startswith('{')]
    if not any(row.get('ok') is True for row in rows):
        raise SystemExit('No successful normal client in '+name+'; capture not registered')
PY_CHECK
fi
"$PYTHON" lab/register_capture.py "$CAPTURE_ROOT" --id "$RUN_ID" --split "$SPLIT" --label "$LABEL" --start "$START" --end "$END"
if [ -n "${SUDO_UID:-}" ]; then chown "$SUDO_UID:${SUDO_GID:-$SUDO_UID}" "$CAPTURE_ROOT/manifest.csv"; fi
"$PYTHON" tools/summarize_sensor.py "$OUT/sensor.jsonl"
if [ "$MODE" = normal ] && [ "$NORMAL_CLIENTS" -eq 2 ]; then
 echo 'Second legitimate MQTT source:'
 "$PYTHON" tools/summarize_sensor.py "$OUT/sensor_extra.jsonl"
fi
echo "Saved $OUT. Check capture.log for dropped packets; a scenario label is not proof of service failure."
