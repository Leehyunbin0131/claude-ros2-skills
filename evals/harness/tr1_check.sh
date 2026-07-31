#!/usr/bin/env bash
# Real-outcome checks for the ros2-troubleshooting executor ladder, rung L1.
#
#   ./tr1_check.sh <cell-workdir> <out.json>
#
# The mechanism and the check that catches it:
#
#   a service called from inside a callback  -> tr1_logs_5, tr1_no_hang
#     SKILL.md §3C claims this "hangs the entire node". Validating the graders
#     showed that is only half right on Jazzy, and the wrong half is the one
#     the file states:
#
#       nested spin (spin_until_future_complete inside a callback while
#       rclpy.spin is running)  -> NOT a hang. rclpy raises
#       RuntimeError("Executor is already spinning") in ~1 s. Loud, immediate,
#       impossible to miss.
#
#       spin_until_future_complete(node, fut) with no executor argument, while
#       the node is on a MultiThreadedExecutor spinning elsewhere -> THIS is
#       the silent hang. It builds a second SingleThreadedExecutor behind your
#       back and waits forever, with no output at all.
#
#     Both are graded here, and they fail through different checks, which is
#     what makes the diagnosis mechanical.
#
# Graded by RUNNING the cell's node.py against a live /slow_check server. The
# only question is whether the artifact works, so nothing here reads the source.
#
# Traps this file is written downstream of, all paid for in earlier rounds:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#     because grep -q exits early and SIGPIPEs the producer. Capture, then match.
#   * assert nothing the frozen prompt does not require. The prompt names the
#     log format and the exit code; those are fair. It does not name a file
#     layout beyond node.py, an executor type, or an API, so none is checked.
#   * kill leftovers with -9 before and after; a hung cell from a previous run
#     would otherwise still hold the service.
set -uo pipefail

WORK="${1:?usage: tr1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: tr1_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"tr1_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

# Anchored to `python3 <path>` so the pattern cannot match a wrapper shell whose
# command line merely contains the path -- the same mistake that had
# `pkill -f "gz sim"` killing its own parent in the gazebo rounds.
kill_all() {
  pkill -9 -f '^python3 .*slow_trigger_server\.py' 2>/dev/null || true
  pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true
}
kill_all
sleep 1

# --- scenario: the deliberately slow service -------------------------------
SRV_LOG="$(mktemp)"
python3 "$HARNESS/slow_trigger_server.py" >"$SRV_LOG" 2>&1 &
SRV=$!
for _ in $(seq 1 20); do
  SL="$(timeout 5 ros2 service list 2>/dev/null || true)"
  case "$SL" in */slow_check*) break ;; esac
  sleep 1
done

# --- run the cell's node ----------------------------------------------------
# 5 results at 1 s each needs ~5 s. 45 s is generous for a working node and
# unreachable for a deadlocked one, which hangs forever.
RUN_LOG="$(mktemp)"
START=$(date +%s)
timeout 45 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))

# kill_all sends -9, and it goes FIRST. `kill $SRV` then `wait $SRV` hung the
# L3 checker for 4.8 hours on a live round: rclpy inside executor.spin() does
# not reliably act on SIGTERM, and `wait` on a still-live child never returns.
kill_all
wait $SRV 2>/dev/null || true

# `grep -c` prints 0 AND exits non-zero on no match, so `|| echo 0` appends a
# SECOND zero and printf %d then chokes on "0\n0". Count with awk instead.
N_RESULTS=$(awk '/RESULT/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

p_found=true
p_logs5=false;  [ "${N_RESULTS:-0}" -ge 5 ] && p_logs5=true
# 124 is `timeout`'s SIGTERM code: the node never finished.
p_nohang=false; [ "$RC" -ne 124 ] && p_nohang=true
p_clean=false;  [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "tr1_node_found": %s,\n'  "$p_found"
  printf '  "node": %s,\n'            "$(printf '%s' "$NODE" | json_escape)"
  printf '  "tr1_logs_5": %s,\n'      "$p_logs5"
  printf '  "tr1_no_hang": %s,\n'     "$p_nohang"
  printf '  "tr1_exits_clean": %s,\n' "$p_clean"
  printf '  "n_results": %d,\n'       "${N_RESULTS:-0}"
  printf '  "exit_code": %d,\n'       "$RC"
  printf '  "elapsed_s": %d,\n'       "$ELAPSED"
  printf '  "run_tail": %s\n'         "$(tail -c 1500 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$SRV_LOG"
