#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(id -u)" -eq 0 ]; then echo 'Run as your normal Ubuntu user; script asks sudo only for apt.' >&2; exit 1; fi
sudo apt-get update
# Distribution packages support Ubuntu's own Python (including newer Ubuntu releases).
sudo apt-get install -y python3 python3-venv python3-pip python3-numpy python3-sklearn python3-scapy python3-paho-mqtt python3-serial mosquitto mosquitto-clients tcpdump iproute2 iptables iverilog unzip
python3 -m venv --system-site-packages .venv
.venv/bin/python tools/check_environment.py
printf '\nInstalled. Next: bash scripts/selfcheck.sh\n'
