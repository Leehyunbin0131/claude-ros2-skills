#!/usr/bin/env bash
# Real-outcome checks for the ros2-troubleshooting executor ladder, rung L2.
#
#   ./tr2_check.sh <cell-workdir> <out.json>
#
# L2 adds over L1: the service call moves into a SUBSCRIPTION callback, and the
# node must hold its own 10 Hz `/heartbeat` while calls are in flight. That
# second requirement is the whole rung -- it is what separates "the node
# finished" from "the node stayed responsive", and only the second one exposes a
# callback-group mistake.
#
#   service called from a subscription callback -> tr2_logs_5, tr2_no_hang
#   the executor is not starved while it waits  -> tr2_heartbeat_steady
#     A timer and a subscription that share one MutuallyExclusiveCallbackGroup
#     (rclpy's default for everything on a node) cannot run concurrently, so a
#     1 s blocking call in the subscription leaves a 1 s hole in a stream that
#     should have no gap wider than 0.1 s. Measured as MAX GAP, not average
#     rate: the average hides one-second holes, the max gap cannot.
#
# Graded by running the cell's node.py against a live service and tick source.
# Nothing reads the source -- an executor choice that works is not wrong.
#
# Traps this file is written downstream of:
#   * no `cmd | grep -q X` (pipefail turns a match into a failure)
#   * no `grep -c` for counting (prints 0 AND exits 1; `|| echo 0` then yields
#     "0\n0" and printf %d chokes). awk instead.
#   * pkill patterns anchored to `^python3 ` so they cannot match a wrapper
#     shell whose command line merely contains the path.
#   * assert nothing the frozen prompt does not require.
set -uo pipefail

WORK="${1:?usage: tr2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tr2_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"tr2_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^python3 .*slow_trigger_server\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*tick_publisher\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*heartbeat_monitor\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/slow_trigger_server.py" >/dev/null 2>&1 &
SRV=$!
python3 "$HARNESS/tick_publisher.py" >/dev/null 2>&1 &
TICK=$!
for _ in $(seq 1 20); do
  SL="$(timeout 5 ros2 service list 2>/dev/null || true)"
  case "$SL" in */slow_check*) break ;; esac
  sleep 1
done

HB_JSON="$(mktemp)"
RUN_LOG="$(mktemp)"

# Monitor and node start together; the monitor outlives the node slightly so a
# stall at the very end is still inside its window.
python3 "$HARNESS/heartbeat_monitor.py" "$HB_JSON" 30 >/dev/null 2>&1 &
MON=$!
sleep 1

START=$(date +%s)
timeout 60 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

# kill_all sends -9, and it goes FIRST. Waiting before killing hung the L3
# checker for 4.8 hours on a live round: rclpy inside executor.spin() does not
# reliably act on SIGTERM, and `wait` on a still-live child never returns.
kill_all
wait $MON 2>/dev/null || true
wait $SRV 2>/dev/null || true
wait $TICK 2>/dev/null || true

N_RESULTS=$(awk '/RESULT/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
read -r HB_COUNT HB_MAXGAP HB_HZ <<<"$(python3 -c '
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print("0 -1 0"); raise SystemExit
g=d.get("max_gap_s")
print(d.get("count",0), g if g is not None else -1, d.get("avg_hz",0))' "$HB_JSON")"

p_logs5=false;   [ "${N_RESULTS:-0}" -ge 5 ] && p_logs5=true
p_nohang=false;  [ "$RC" -ne 124 ] && p_nohang=true
p_clean=false;   [ "$RC" -eq 0 ] && p_clean=true
# 10 Hz means 0.1 s between beats. 0.5 s allows generous jitter and scheduling
# noise while still being far below the ~1 s hole a blocked executor leaves.
p_hb=false
python3 -c '
import sys
c, g = int(sys.argv[1]), float(sys.argv[2])
sys.exit(0 if (c >= 20 and 0 <= g < 0.5) else 1)' "$HB_COUNT" "$HB_MAXGAP" && p_hb=true

{
  printf '{\n'
  printf '  "tr2_node_found": true,\n'
  printf '  "node": %s,\n'                 "$(printf '%s' "$NODE" | json_escape)"
  printf '  "tr2_logs_5": %s,\n'           "$p_logs5"
  printf '  "tr2_no_hang": %s,\n'          "$p_nohang"
  printf '  "tr2_exits_clean": %s,\n'      "$p_clean"
  printf '  "tr2_heartbeat_steady": %s,\n' "$p_hb"
  printf '  "n_results": %d,\n'            "${N_RESULTS:-0}"
  printf '  "hb_count": %d,\n'             "${HB_COUNT:-0}"
  printf '  "hb_max_gap_s": %s,\n'         "${HB_MAXGAP:--1}"
  printf '  "hb_avg_hz": %s,\n'            "${HB_HZ:-0}"
  printf '  "exit_code": %d,\n'            "$RC"
  printf '  "elapsed_s": %d,\n'            "$ELAPSED"
  printf '  "run_tail": %s\n'              "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$HB_JSON"
