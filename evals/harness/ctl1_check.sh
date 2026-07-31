#!/usr/bin/env bash
# Real-outcome checks for the ros2-control ladder, rung L1.
#
#   ./ctl1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   URDF <ros2_control> + mock_components/GenericSystem  -> ctl1_joint_states
#   controller_manager brought up with a params YAML     -> ctl1_cm_running
#   joint_state_broadcaster spawned (it is NOT automatic) -> ctl1_jsb_active
#
# `joint_state_broadcaster` not being started automatically is the classic
# silent failure here: everything else comes up, `ros2 control list_controllers`
# looks plausible, and /joint_states is simply never published.
#
# Graded by RUNNING the cell's bringup.sh and then querying the live system.
# Nothing reads the source: a launch file, a raw ros2_control_node invocation or
# anything else that works is equally correct.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * pkill anchored so it cannot match a wrapper shell
#   * controller_manager IGNORES SIGTERM -- kill -9, and never `wait` on it
#   * ROS_DOMAIN_ID isolation: ten stray ros2_control_node processes from an
#     earlier round were found alive on the default domain days later
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: ctl1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: ctl1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"ctl1_bringup_found": false}\n' > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f '^/opt/ros/jazzy/lib/controller_manager/ros2_control_node' 2>/dev/null || true
  pkill -9 -f 'ros2_control_node' 2>/dev/null || true
  pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
  pkill -9 -f 'spawner' 2>/dev/null || true
  pkill -9 -f '^python3 .*bringup' 2>/dev/null || true
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

# If the cell built a workspace, its install tree has to be on the path for the
# bringup to find anything it created. Sourcing it is part of using what the
# cell produced, not a hint.
if [ -f "$BDIR/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source "$BDIR/install/setup.bash"
  set -u
fi

BRING_LOG="$(mktemp)"
( cd "$BDIR" && timeout 120 bash ./bringup.sh ) >"$BRING_LOG" 2>&1
BRING_RC=$?

# The cell's bringup may set its own ROS_DOMAIN_ID -- correct practice, and
# invisible unless we ask. See ctl2_check.sh: two L2 cells that did this were
# scored as total failures by a checker that kept querying its own domain.
# Every ctl1 cell happened to inherit ours, so no ctl1 result changes; the fix
# is here so the next one does not depend on that.
adopt_domain_from() {
  local pid d
  pid="$(pgrep -f "$1" | head -1)"
  [ -n "$pid" ] || return 0
  d="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
       | awk -F= '$1=="ROS_DOMAIN_ID" {print $2; exit}')"
  [ -n "$d" ] && export ROS_DOMAIN_ID="$d"
  return 0
}
adopt_domain_from 'ros2_control_node'

# Give the system time to come up. The prompt says bringup starts things in the
# background and returns, so the interesting state appears after it exits.
CM_SEEN=false
for _ in $(seq 1 40); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *controller_manager*) CM_SEEN=true; break ;; esac
  sleep 1
done

LC_OUT="$(timeout 20 ros2 control list_controllers 2>&1)"
JSB_ACTIVE=false
if printf '%s' "$LC_OUT" | awk '/joint_state_broadcaster/ && /active/ {found=1} END {exit !found}'; then
  JSB_ACTIVE=true
fi

# /joint_states must carry BOTH joints. A broadcaster that is active but wired
# to nothing publishes an empty name array, which is the failure this catches.
JS_OUT="$(timeout 25 ros2 topic echo /joint_states --once 2>&1)"
JS_BOTH=false
if printf '%s' "$JS_OUT" | awk '/joint_a/ {a=1} /joint_b/ {b=1} END {exit !(a && b)}'; then
  JS_BOTH=true
fi

kill_all

p_cm=false;  $CM_SEEN && p_cm=true
p_jsb=false; $JSB_ACTIVE && p_jsb=true
p_js=false;  $JS_BOTH && p_js=true

{
  printf '{\n'
  printf '  "ctl1_bringup_found": true,\n'
  printf '  "bringup": %s,\n'            "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "ctl1_cm_running": %s,\n'    "$p_cm"
  printf '  "ctl1_jsb_active": %s,\n'    "$p_jsb"
  printf '  "ctl1_joint_states": %s,\n'  "$p_js"
  printf '  "bringup_rc": %d,\n'         "$BRING_RC"
  printf '  "list_controllers": %s,\n'   "$(printf '%s' "$LC_OUT" | head -c 800 | json_escape)"
  printf '  "joint_states": %s,\n'       "$(printf '%s' "$JS_OUT" | head -c 800 | json_escape)"
  printf '  "bringup_tail": %s\n'        "$(tail -c 1200 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG"
