#!/usr/bin/env bash
# Real-outcome checks for the ros2-core ladder, rung L2.
#
#   ./cor2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a dynamic transform broadcast at 20 Hz    -> cor2_tf_lines
#   x advancing 0.05 m per second             -> cor2_motion
#   a future lookup handled, not crashed      -> cor2_extrap
#
# `cor2_extrap` is the rung. Looking a transform up 5 s in the future raises
# `ExtrapolationException`; the prompt asks for the message to be logged and
# the node to keep going. A node that lets it propagate dies before its 20 TF
# lines, so the two failures are distinguishable: no EXTRAP line at all versus
# an EXTRAP line and a clean exit.
#
# `cor2_motion` is graded from the values the node logs, because the frozen
# prompt fixes that contract: `TF <t> <x>` per broadcast. How the lookup is
# done is the cell's choice and is not graded.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * pkill anchored to `^python3 `
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: cor2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: cor2_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"cor2_node_found": false}\n' > "$OUT"
  exit 0
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() { pkill -9 -f '^python3 .*/node\.py' 2>/dev/null || true; }
kill_all
sleep 1

RUN_LOG="$(mktemp)"
START=$(date +%s)
timeout 90 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))
kill_all

N_TF=$(awk '/TF / {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)
N_EXTRAP=$(awk '/EXTRAP/ {n++} END {print n+0}' "$RUN_LOG" 2>/dev/null)

# x must advance. Compare the first and last logged x: at 0.05 m/s over the
# 20 broadcasts the prompt asks for (1 s at 20 Hz) that is about 0.05 m, so
# require any clear increase rather than a specific value the prompt never
# fixes.
read -r X_FIRST X_LAST <<<"$(awk '
  /TF / {
    for (i = 1; i <= NF; i++) if ($i ~ /TF/) { x = $(i+2) + 0; break }
    if (!seen) { first = x; seen = 1 }
    last = x
  }
  END { printf "%.5f %.5f", first+0, last+0 }' "$RUN_LOG" 2>/dev/null)"

MOTION=false
awk -v a="$X_FIRST" -v b="$X_LAST" 'BEGIN { exit !(b - a > 0.005) }' && MOTION=true

p_lines=false;  [ "${N_TF:-0}" -ge 20 ] && p_lines=true
p_motion=false; $MOTION && p_motion=true
p_extrap=false; [ "${N_EXTRAP:-0}" -ge 1 ] && p_extrap=true
p_clean=false;  [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "cor2_node_found": true,\n'
  printf '  "node": %s,\n'             "$(printf '%s' "$NODE" | json_escape)"
  printf '  "cor2_tf_lines": %s,\n'    "$p_lines"
  printf '  "cor2_motion": %s,\n'      "$p_motion"
  printf '  "cor2_extrap": %s,\n'      "$p_extrap"
  printf '  "cor2_exits_clean": %s,\n' "$p_clean"
  printf '  "n_tf_lines": %d,\n'       "${N_TF:-0}"
  printf '  "n_extrap_lines": %d,\n'   "${N_EXTRAP:-0}"
  printf '  "x_first": %s,\n'          "$(printf '%s' "${X_FIRST:-0}" | json_escape)"
  printf '  "x_last": %s,\n'           "$(printf '%s' "${X_LAST:-0}" | json_escape)"
  printf '  "exit_code": %d,\n'        "$RC"
  printf '  "elapsed_s": %d,\n'        "$ELAPSED"
  printf '  "run_tail": %s\n'          "$(tail -c 1200 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG"
