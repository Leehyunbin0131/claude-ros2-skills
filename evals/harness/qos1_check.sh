#!/usr/bin/env bash
# Real-outcome checks for the ros2-troubleshooting QoS ladder, rung L1.
#
#   ./qos1_check.sh <cell-workdir> <out.json>
#
# The mechanism and the check that catches it:
#
#   reliability mismatch -> qos1_receives
#     `/sensor` is offered BEST_EFFORT. rclpy's default subscriber is RELIABLE,
#     and RELIABLE cannot match a BEST_EFFORT offer, so the callback never
#     fires. Verified on this install before the rung ran: a default subscriber
#     gets 0 messages in 5 s, a BEST_EFFORT one gets 99.
#
# Graded by RUNNING the cell's node.py against a live publisher. Nothing reads
# the source -- SensorDataQoS, an explicit QoSProfile or anything else that
# works is equally correct.
#
# NOTE on coupling, stated rather than implied: at this rung the three checks
# are not independent. A node that receives nothing cannot log 20 messages and
# therefore cannot exit 0 either, so the `default_reliable` reference fails all
# three. `qos1_receives` is the one the rung is about; the other two exist to
# catch a node that receives but then mishandles its own exit.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1, so `|| echo 0` yields
#     "0\n0" and printf %d chokes. awk instead.
#   * pkill anchored to `^python3 ` so it cannot match a wrapper shell
#   * kill -9, and never `wait` on a child that may ignore SIGTERM: rclpy inside
#     spin() does not reliably act on it, and that hung a checker for 4 h 48 m
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: qos1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: qos1_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"qos1_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^python3 .*qos_publishers\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/qos_publishers.py" >/dev/null 2>&1 &
SRV=$!
for _ in $(seq 1 20); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in */sensor*) break ;; esac
  sleep 1
done

RUN_LOG="$(mktemp)"
# 20 messages at 20 Hz needs 1 s. 40 s is unreachable for a subscriber that
# never matches, and generous for one that does.
START=$(date +%s)
timeout 40 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

kill_all
wait $SRV 2>/dev/null || true

N_GOT=$(awk '/GOT/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
# Jazzy WARNs on an incompatible match rather than failing entirely silently.
# Recorded, not scored: the rung is about whether data arrives.
SAW_WARN=$(awk '/incompatible QoS/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

p_recv=false;   [ "${N_GOT:-0}" -ge 20 ] && p_recv=true
p_nohang=false; [ "$RC" -ne 124 ] && p_nohang=true
p_clean=false;  [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "qos1_node_found": true,\n'
  printf '  "node": %s,\n'              "$(printf '%s' "$NODE" | json_escape)"
  printf '  "qos1_receives": %s,\n'     "$p_recv"
  printf '  "qos1_no_hang": %s,\n'      "$p_nohang"
  printf '  "qos1_exits_clean": %s,\n'  "$p_clean"
  printf '  "n_got": %d,\n'             "${N_GOT:-0}"
  printf '  "saw_incompat_warn": %d,\n' "${SAW_WARN:-0}"
  printf '  "exit_code": %d,\n'         "$RC"
  printf '  "elapsed_s": %d,\n'         "$ELAPSED"
  printf '  "run_tail": %s\n'           "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG"
