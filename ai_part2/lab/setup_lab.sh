#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MARKER="$PWD/build/lab.created"
[ "$(id -u)" -eq 0 ] || { echo 'Use sudo bash lab/setup_lab.sh up|down'; exit 1; }
mkdir -p build
names=(p2broker p2sensor p2source)
host_links=(p2brokerh p2sensorh p2sourceh)
OWNER="ai_part2:$(pwd -P)"
cleanup_owned() {
 for ns in "${names[@]}"; do
  if ip netns list | awk '{print $1}' | grep -qx "$ns"; then
   for pid in $(ip netns pids "$ns"); do kill "$pid" 2>/dev/null || true; done
  fi
 done
 # TERM and removal of the namespace name do not guarantee its final process
 # has exited. Delete the owned host endpoints explicitly, while ownership is
 # still recorded; otherwise a living unnamed namespace can retain its veth.
 for link in "${host_links[@]}"; do
  if ip link show "$link" >/dev/null 2>&1; then
   if ! ip link del "$link" 2>/dev/null; then
    if ip link show "$link" >/dev/null 2>&1; then echo "Cannot remove owned link: $link";return 1;fi
   fi
  fi
 done
 for ns in "${names[@]}"; do
  if ip netns list | awk '{print $1}' | grep -qx "$ns"; then ip netns del "$ns"; fi
 done
 ip link del p2br 2>/dev/null || true
 for link in "${host_links[@]}" p2br; do
  if ip link show "$link" >/dev/null 2>&1; then echo "Cleanup incomplete: $link remains; ownership marker retained";return 1;fi
 done
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
  created=();created_links=()
  trap 'for l in "${created_links[@]}"; do ip link del "$l" 2>/dev/null || true; done; for n in "${created[@]}"; do ip netns del "$n" 2>/dev/null || true; done; ip link del p2br 2>/dev/null || true' ERR
  ip link add p2br type bridge
  ip link set p2br alias "$OWNER"
  ip link set p2br up
  i=1
  for ns in "${names[@]}"; do
   ip netns add "$ns";created+=("$ns")
   ip link add "${ns}h" type veth peer name eth0 netns "$ns"
   created_links+=("${ns}h")
   ip link set "${ns}h" alias "$OWNER"
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
  [ "$(cat "$MARKER")" = 'Created by ai_part2 lab/setup_lab.sh' ] || { echo 'Unexpected ownership marker';exit 1; }
  cleanup_owned
  echo 'Lab DOWN'
  ;;
 *) echo 'Usage: sudo bash lab/setup_lab.sh up|down';exit 1;;
esac
