#!/usr/bin/env bash
# Real-outcome checks for the ros2-core ladder, rung L1.
#
#   ./cor1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a static transform broadcast and looked back up -> cor1_tf_logged
#   the translation read back correctly             -> cor1_tf_correct
#   ROS parameters actually driving the values      -> cor1_params_used
#
# `cor1_params_used` is what separates a node that declares `tx`/`ty`/`tz` from
# one that hardcodes 0.2/0.0/0.1 and prints them. The check re-runs the node
# with `--ros-args -p tx:=0.7`, which a hardcoding node ignores.
#
# `cor1_tf_correct` is graded on the values the node itself logs, because the
# frozen prompt fixes that contract: a `TF <x> <y> <z>` line. How the lookup is
# done -- Buffer/TransformListener, a static broadcaster plus wait -- is the
# cell's choice and is not graded.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * pkill anchored to `^python3 `
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: cor1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: cor1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

NODE="$(find "$WORK" -maxdepth 3 -name 'node.py' -print -quit 2>/dev/null)"
if [ -z "$NODE" ]; then
  printf '{"cor1_node_found": false}\n' > "$OUT"
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

# --- default run -------------------------------------------------------------
RUN_LOG="$(mktemp)"
START=$(date +%s)
timeout 60 python3 "$NODE" >"$RUN_LOG" 2>&1
RC=$?
ELAPSED=$(( $(date +%s) - START ))
kill_all

read -r N_TF X Y Z <<<"$(awk '
  /TF/ {
    for (i = 1; i <= NF; i++) if ($i ~ /TF/) { x = $(i+1) + 0; y = $(i+2) + 0; z = $(i+3) + 0; break }
    n++
  }
  END { printf "%d %.4f %.4f %.4f", n+0, x, y, z }' "$RUN_LOG" 2>/dev/null)"

TF_OK=false
if [ "${N_TF:-0}" -ge 1 ] && awk -v x="$X" -v y="$Y" -v z="$Z" \
     'BEGIN { exit !( (x-0.2<0.01 && 0.2-x<0.01) && (y<0.01 && -y<0.01) && (z-0.1<0.01 && 0.1-z<0.01) ) }'; then
  TF_OK=true
fi

# --- parameter override ------------------------------------------------------
# A node that hardcodes the translation prints 0.2 again here.
PARAM_LOG="$(mktemp)"
timeout 60 python3 "$NODE" --ros-args -p tx:=0.7 >"$PARAM_LOG" 2>&1
PARAM_RC=$?
kill_all

read -r N_TF2 X2 <<<"$(awk '
  /TF/ { for (i = 1; i <= NF; i++) if ($i ~ /TF/) { x = $(i+1) + 0; break } n++ }
  END { printf "%d %.4f", n+0, x }' "$PARAM_LOG" 2>/dev/null)"

PARAMS_OK=false
if [ "${N_TF2:-0}" -ge 1 ] && awk -v x="$X2" \
     'BEGIN { exit !( x-0.7<0.01 && 0.7-x<0.01 ) }'; then
  PARAMS_OK=true
fi

p_logged=false; [ "${N_TF:-0}" -ge 1 ] && p_logged=true
p_correct=false; $TF_OK && p_correct=true
p_params=false;  $PARAMS_OK && p_params=true
p_clean=false;   [ "$RC" -eq 0 ] && p_clean=true

{
  printf '{\n'
  printf '  "cor1_node_found": true,\n'
  printf '  "node": %s,\n'              "$(printf '%s' "$NODE" | json_escape)"
  printf '  "cor1_tf_logged": %s,\n'    "$p_logged"
  printf '  "cor1_tf_correct": %s,\n'   "$p_correct"
  printf '  "cor1_params_used": %s,\n'  "$p_params"
  printf '  "cor1_exits_clean": %s,\n'  "$p_clean"
  printf '  "n_tf_lines": %d,\n'        "${N_TF:-0}"
  printf '  "xyz": %s,\n'               "$(printf '%s %s %s' "$X" "$Y" "$Z" | json_escape)"
  printf '  "x_with_param": %s,\n'      "$(printf '%s' "$X2" | json_escape)"
  printf '  "exit_code": %d,\n'         "$RC"
  printf '  "param_exit_code": %d,\n'   "$PARAM_RC"
  printf '  "elapsed_s": %d,\n'         "$ELAPSED"
  printf '  "run_tail": %s\n'           "$(tail -c 1000 "$RUN_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$RUN_LOG" "$PARAM_LOG"
