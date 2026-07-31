#!/usr/bin/env bash
# Real-outcome checks for the ros2-moveit ladder, rung L2.
#
#   ./mvt2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   move_group reaching a usable state          -> mvt2_move_group_up
#   plan.py running against it without crashing -> mvt2_plan_runs
#   a plan actually coming back with a path     -> mvt2_points
#
# `mvt2_points` is the rung. L1 only needed move_group to load a robot model;
# here a plan must be requested and a trajectory returned. A setup whose
# planning pipeline is misconfigured still passes L1 completely -- move_group
# starts, the SRDF loads, /plan_kinematic_path is offered -- and then every
# planning request fails. That is exactly the shape the reference below
# reproduces.
#
# Graded by RUNNING the cell's own plan.py and reading its stdout, because the
# frozen prompt specifies that contract: a `POINTS <n>` line with n > 1. How the
# plan is requested -- the service, MoveGroupInterface, moveit_py -- is the
# cell's choice and is not graded.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * kill -9, never `wait` on a child that may ignore SIGTERM
#   * bounded wait loops, so the three of them cannot outlast the caller's
#     timeout and leave no out.json at all
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: mvt2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: mvt2_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
PLAN="$(find "$WORK" -maxdepth 3 -name 'plan.py' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ] || [ -z "$PLAN" ]; then
  printf '{"mvt2_bringup_found": %s}\n' \
    "$([ -n "$BRINGUP" ] && [ -n "$PLAN" ] && echo true || echo false)" > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'move_group' 2>/dev/null || true
  pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
  pkill -9 -f 'joint_state_publisher' 2>/dev/null || true
  pkill -9 -f 'static_transform_publisher' 2>/dev/null || true
  # Also kill anything still referencing the cell's own directory. The cell has
  # already run its bringup once -- CLAUDE.md tells it to verify its work -- and
  # killing only the nodes left the `ros2 launch` wrapper alive, so a bringup
  # guarded by `pgrep -f bringup_launch.py` reported "already running, skipping"
  # and started nothing. That scored a working cell as a total failure.
  #
  # Self-exclusion is not optional: this checker's own command line contains
  # BDIR, so a bare `pkill -f "$BDIR"` kills the checker mid-run (rc 137, no
  # verdict written). Skip this shell and every ancestor of it.
  if [ -n "${BDIR:-}" ]; then
    local skip=" $$ " p=$PPID
    while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
      skip="$skip$p "
      p="$(awk '{print $4}' "/proc/$p/stat" 2>/dev/null)"
    done
    local pid
    for pid in $(pgrep -f "$BDIR" 2>/dev/null || true); do
      case "$skip" in *" $pid "*) continue ;; esac
      kill -9 "$pid" 2>/dev/null || true
    done
  fi
}
kill_all
sleep 1

if [ -f "$BDIR/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$BDIR/install/setup.bash"
  set -u
fi

BRING_LOG="$(mktemp)"
( cd "$BDIR" && timeout 180 bash ./bringup.sh ) >"$BRING_LOG" 2>&1
BRING_RC=$?

# The cell's bringup may set its own ROS_DOMAIN_ID -- correct practice, and
# invisible unless we ask. An L2 cell that did this planned 21 points while
# this checker reported move_group_up=false, because `ros2 node list` was
# querying a different domain.
adopt_domain_from() {
  local pid d
  pid="$(pgrep -f "$1" | head -1)"
  [ -n "$pid" ] || return 0
  d="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
       | awk -F= '$1=="ROS_DOMAIN_ID" {print $2; exit}')"
  [ -n "$d" ] && export ROS_DOMAIN_ID="$d"
  return 0
}
adopt_domain_from 'move_group'

MG_UP=false
for _ in $(seq 1 45); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *move_group*) MG_UP=true; break ;; esac
  sleep 1
done

PLAN_LOG="$(mktemp)"
START=$(date +%s)
( cd "$BDIR" && timeout 120 python3 ./plan.py ) >"$PLAN_LOG" 2>&1
PLAN_RC=$?
ELAPSED=$(( $(date +%s) - START ))

kill_all

# POINTS <n>, n > 1. Take the largest reported, so a cell that prints a
# progress line before the final answer is not punished for the earlier one.
N_POINTS=$(awk '
  /POINTS/ {
    for (i = 1; i <= NF; i++) if ($i ~ /POINTS/) { v = $(i+1) + 0; if (v > m) m = v }
  }
  END { print m+0 }' "$PLAN_LOG" 2>/dev/null)

p_mg=false;     $MG_UP && p_mg=true
p_runs=false;   [ "$PLAN_RC" -eq 0 ] && p_runs=true
p_points=false; [ "${N_POINTS:-0}" -gt 1 ] && p_points=true

{
  printf '{\n'
  printf '  "mvt2_bringup_found": true,\n'
  printf '  "bringup": %s,\n'            "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "plan": %s,\n'               "$(printf '%s' "$PLAN" | json_escape)"
  printf '  "mvt2_move_group_up": %s,\n' "$p_mg"
  printf '  "mvt2_plan_runs": %s,\n'     "$p_runs"
  printf '  "mvt2_points": %s,\n'        "$p_points"
  printf '  "n_points": %d,\n'           "${N_POINTS:-0}"
  printf '  "plan_rc": %d,\n'            "$PLAN_RC"
  printf '  "bringup_rc": %d,\n'         "$BRING_RC"
  printf '  "elapsed_s": %d,\n'          "$ELAPSED"
  printf '  "plan_tail": %s,\n'          "$(tail -c 1200 "$PLAN_LOG" | json_escape)"
  printf '  "bringup_tail": %s\n'        "$(tail -c 1000 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG" "$PLAN_LOG"
