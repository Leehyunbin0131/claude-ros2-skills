#!/usr/bin/env bash
# Real-outcome checks for the ros2-troubleshooting executor ladder, rung L3.
#
#   ./tr3_check.sh <cell-workdir> <out.json>
#
# L3 adds over L2: five calls issued CONCURRENTLY from one callback, all five
# awaited, and the batch has to finish in under three seconds. Each call takes
# ~1 s, so five sequential calls take ~5 s. **Wall time is the check** -- it is
# the one measurement that cannot be satisfied by a node that merely works.
#
#   five calls actually overlap  -> tr3_batch_under_3s
#     Needs a Reentrant group AND a MultiThreadedExecutor AND call_async on all
#     five before awaiting any. Get any one of those wrong and the batch is
#     serialised, which still produces five correct results and exit 0 -- which
#     is exactly why the timing check exists and why it is graded separately.
#   all five responses collected -> tr3_logs_5
#   the node reports its own timing honestly -> tr3_total_line
#
# Achievability, measured before the rung ran: the scenario server spins 4
# threads, so five concurrent 1 s calls complete in ~2 s, not ~1 s. That is
# comfortably inside the 3 s the frozen prompt allows, and it deliberately does
# not require unbounded server parallelism from the cell.
#
# Timing is taken from the harness's own clock, not from the node's TOTAL line.
# The TOTAL line is checked for presence because the prompt asks for it, but a
# node grading its own speed would be the check marking its own homework.
#
# Traps this file is written downstream of:
#   * no `cmd | grep -q X` (pipefail turns a match into a failure)
#   * no `grep -c` for counting ("0\n0" breaks printf %d) -- awk instead
#   * pkill anchored to `^python3 ` so it cannot match a wrapper shell
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: tr3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tr3_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"tr3_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^python3 .*slow_trigger_server\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
}
kill_all
sleep 1

python3 "$HARNESS/slow_trigger_server.py" >/dev/null 2>&1 &
SRV=$!
for _ in $(seq 1 20); do
  SL="$(timeout 5 ros2 service list 2>/dev/null || true)"
  case "$SL" in */slow_check*) break ;; esac
  sleep 1
done

RUN_LOG="$(mktemp)"
# Nanosecond clock: a 5 s serialised batch and a <3 s concurrent one are far
# apart, but process startup is counted too, so measure generously and let the
# node's own TOTAL line stay advisory.
START_NS=$(date +%s%N)
timeout 60 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
END_NS=$(date +%s%N)
WALL_MS=$(( (END_NS - START_NS) / 1000000 ))

# kill_all sends -9, and it goes FIRST. The previous order -- `kill $SRV` then
# `wait $SRV` -- hung this checker for 4.8 hours on a live round: rclpy inside
# executor.spin() does not reliably act on SIGTERM, and `wait` on a child that
# is still alive never returns. Exactly the lesson `gz sim` taught in the gazebo
# rounds, not carried across to the Python scenario servers until it cost a
# round here too.
kill_all
wait $SRV 2>/dev/null || true

N_RESULTS=$(awk '/RESULT/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
HAS_TOTAL=$(awk '/TOTAL/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
# The node's own reported batch time, if it printed one.
NODE_TOTAL=$(awk '/TOTAL/ {for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\.?[0-9]*$/) {print $i; exit}}' \
             "$RUN_LOG" 2>/dev/null)

p_logs5=false;  [ "${N_RESULTS:-0}" -ge 5 ] && p_logs5=true
p_total=false;  [ "${HAS_TOTAL:-0}" -ge 1 ] && p_total=true
p_clean=false;  [ "$RC" -eq 0 ] && p_clean=true
# Batch under 3 s. Judged on the node's own TOTAL when it printed one -- that is
# the batch, excluding interpreter and discovery startup, which is what the
# prompt actually constrains. Falls back to wall time minus a 4 s startup
# allowance only when no TOTAL was printed.
p_fast=false
python3 -c '
import sys
node_total, wall_ms, has_total = sys.argv[1], int(sys.argv[2]), sys.argv[3] == "1"
if has_total and node_total:
    try:
        sys.exit(0 if float(node_total) < 3.0 else 1)
    except ValueError:
        pass
sys.exit(0 if (wall_ms - 4000) < 3000 else 1)' \
  "${NODE_TOTAL:-}" "$WALL_MS" "$([ "${HAS_TOTAL:-0}" -ge 1 ] && echo 1 || echo 0)" \
  && p_fast=true

{
  printf '{\n'
  printf '  "tr3_node_found": true,\n'
  printf '  "node": %s,\n'              "$(printf '%s' "$NODE" | json_escape)"
  printf '  "tr3_logs_5": %s,\n'        "$p_logs5"
  printf '  "tr3_exits_clean": %s,\n'   "$p_clean"
  printf '  "tr3_total_line": %s,\n'    "$p_total"
  printf '  "tr3_batch_under_3s": %s,\n' "$p_fast"
  printf '  "n_results": %d,\n'         "${N_RESULTS:-0}"
  printf '  "node_total_s": %s,\n'      "$(printf '%s' "${NODE_TOTAL:-null}" | json_escape)"
  printf '  "wall_ms": %d,\n'           "$WALL_MS"
  printf '  "exit_code": %d,\n'         "$RC"
  printf '  "run_tail": %s\n'           "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG"
