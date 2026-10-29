#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MARKER="$PWD/build/lab.created"
[ "$(id -u)" -eq 0 ] || { echo 'Use sudo bash lab/setup_lab.sh up|down'; exit 1; }
mkdir -p build
names=(p2broker p2sensor p2source)
cleanup_owned() {
 for ns in "${names[@]}"; do
  if ip netns list | awk '{print $1}' | grep -qx "$ns"; then
   for pid in $(ip netns pids "$ns"); do kill "$pid" 2>/dev/null || true; done
   ip netns del "$ns"
  fi
 done
 ip link del p2br 2>/dev/null || true
 rm -f "$MARKER"
}
case "${1:-}" in
 up)
  [ ! -e "$MARKER" ] || { echo 'Lab already marked as created. Use down first.'; exit 1; }
  for ns in "${names[@]}"; do
   if ip netns list | awk '{print $1}' | grep -qx "$ns"; then echo "Existing namespace $ns; refusing overwrite"; exit 1; fi
  done
  if ip link show p2br >/dev/null 2>&1; then echo 'p2br already exists; refusing overwrite'; exit 1; fi
  for ns in broker sensor source; do
   if ip link show "p2${ns}h" >/dev/null 2>&1; then echo 'Existing veth name'; exit 1; fi
  done
  created=()
  trap 'for n in "${created[@]}"; do ip netns del "$n" 2>/dev/null || true; done; ip link del p2br 2>/dev/null || true' ERR
  ip link add p2br type bridge
  ip link set p2br up
  i=1
  for ns in "${names[@]}"; do
   ip netns add "$ns";created+=("$ns")
   ip link add "${ns}h" type veth peer name eth0 netns "$ns"
   ip link set "${ns}h" master p2br;ip link set "${ns}h" up
   ip netns exec "$ns" ip link set lo up
   ip netns exec "$ns" ip addr add "198.18.0.$i/24" dev eth0
   ip netns exec "$ns" ip link set eth0 up
   i=$((i+1))
  done
  ip netns exec p2source iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
  # No uplink and no default routes; this lab does not change host firewall/sysctls.
  printf 'Created by ai_part2 lab/setup_lab.sh\n' > "$MARKER"
  trap - ERR
  echo 'Lab UP: broker=.1 sensor=.2 source=.3; no external uplink.'
  ;;
 down)
  [ -f "$MARKER" ] || { echo 'No ownership marker; refusing to remove namespaces'; exit 1; }
  cleanup_owned
  echo 'Lab DOWN'
  ;;
 *) echo 'Usage: sudo bash lab/setup_lab.sh up|down';exit 1;;
esac
