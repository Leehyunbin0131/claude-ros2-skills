#!/usr/bin/env bash
# Real-outcome checks for the ros2-moveit ladder, rung L3.
#
#   ./mvt3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   move_group reaching a usable state            -> mvt3_move_group_up
#   plan.py running against it                    -> mvt3_plan_runs
#   a plan coming back with a path                -> mvt3_points
#   a collision object APPLIED to the scene       -> mvt3_objects
#
# `mvt3_objects` is the rung. L2 only needed a plan; here a box has to reach the
# planning scene AND the scene has to report it back. Publishing a
# CollisionObject on /collision_object and never waiting is the usual way this
# fails: the plan still succeeds, the scene is still empty, and only the
# OBJECTS line tells them apart.
#
# Graded from the cell's own plan.py stdout, because the frozen prompt fixes
# that contract: `POINTS <n>` with n > 1 followed by `OBJECTS <m>` with m >= 1.
# How the object is applied -- ApplyPlanningScene, the /planning_scene topic,
# PlanningSceneInterface -- is the cell's choice and is not graded.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * the cell may set its own ROS_DOMAIN_ID (correct practice) -- adopt it
#   * the cell already ran its bringup, so kill the `ros2 launch` wrapper too
#     or a re-entrancy guard skips the relaunch and nothing starts
#   * `pkill -f "$BDIR"` matches this checker's own command line -- exclude self
#     and every ancestor, or it kills itself mid-run
#   * bounded wait loops, so out.json always gets written
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: mvt3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: mvt3_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
PLAN="$(find "$WORK" -maxdepth 3 -name 'plan.py' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ] || [ -z "$PLAN" ]; then
  printf '{"mvt3_bringup_found": false}\n' > "$OUT"
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
( cd "$BDIR" && timeout 150 python3 ./plan.py ) >"$PLAN_LOG" 2>&1
PLAN_RC=$?
ELAPSED=$(( $(date +%s) - START ))

kill_all

N_POINTS=$(awk '
  /POINTS/ { for (i = 1; i <= NF; i++) if ($i ~ /POINTS/) { v = $(i+1) + 0; if (v > m) m = v } }
  END { print m+0 }' "$PLAN_LOG" 2>/dev/null)
N_OBJECTS=$(awk '
  /OBJECTS/ { for (i = 1; i <= NF; i++) if ($i ~ /OBJECTS/) { v = $(i+1) + 0; if (v > m) m = v } }
  END { print m+0 }' "$PLAN_LOG" 2>/dev/null)

p_mg=false;      $MG_UP && p_mg=true
p_runs=false;    [ "$PLAN_RC" -eq 0 ] && p_runs=true
p_points=false;  [ "${N_POINTS:-0}" -gt 1 ] && p_points=true
p_objects=false; [ "${N_OBJECTS:-0}" -ge 1 ] && p_objects=true

{
  printf '{\n'
  printf '  "mvt3_bringup_found": true,\n'
  printf '  "bringup": %s,\n'            "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "plan": %s,\n'               "$(printf '%s' "$PLAN" | json_escape)"
  printf '  "mvt3_move_group_up": %s,\n' "$p_mg"
  printf '  "mvt3_plan_runs": %s,\n'     "$p_runs"
  printf '  "mvt3_points": %s,\n'        "$p_points"
  printf '  "mvt3_objects": %s,\n'       "$p_objects"
  printf '  "n_points": %d,\n'           "${N_POINTS:-0}"
  printf '  "n_objects": %d,\n'          "${N_OBJECTS:-0}"
  printf '  "plan_rc": %d,\n'            "$PLAN_RC"
  printf '  "bringup_rc": %d,\n'         "$BRING_RC"
  printf '  "elapsed_s": %d,\n'          "$ELAPSED"
  printf '  "plan_tail": %s,\n'          "$(tail -c 1200 "$PLAN_LOG" | json_escape)"
  printf '  "bringup_tail": %s\n'        "$(tail -c 1000 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG" "$PLAN_LOG"
