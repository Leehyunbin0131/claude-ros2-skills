#!/usr/bin/env bash
# Real-outcome checks for the ros2-control ladder, rung L3.
#
#   ./ctl3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a colcon workspace that builds a C++ package        -> ctl3_builds
#   a CUSTOM SystemInterface plugin, not mock_components -> ctl3_custom_plugin
#   that component reaching the active state             -> ctl3_component_active
#   /joint_states carrying both joints through it        -> ctl3_joint_states
#
# `ctl3_custom_plugin` is the rung. The prompt asks for a hardware plugin the
# cell writes itself; a workspace that quietly falls back to
# `mock_components/GenericSystem` satisfies every other check here. It is graded
# from what `ros2 control list_hardware_components` reports at runtime, not from
# reading the source, so any plugin name the cell chooses is accepted as long as
# it is not one of the shipped mock components.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * controller_manager IGNORES SIGTERM -- kill -9, never `wait` on it
#   * the cell may set its own ROS_DOMAIN_ID (correct practice) -- adopt it
#   * the cell has already run its own bringup, so kill the `ros2 launch`
#     wrapper too or a re-entrancy guard will skip the relaunch
#   * `pkill -f "$BDIR"` matches this checker's own command line -- exclude self
#     and every ancestor, or it kills itself mid-run
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: ctl3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: ctl3_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"ctl3_bringup_found": false}\n' > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

# The workspace may sit beside bringup.sh or under it.
WS=""
while IFS= read -r d; do
  [ -n "$(find "$d/src" -maxdepth 3 -name package.xml -print -quit 2>/dev/null)" ] || continue
  WS="$d"; break
done < <(find "$WORK" -maxdepth 4 -type d -name src -printf '%h\n' 2>/dev/null | sort)

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'ros2_control_node' 2>/dev/null || true
  pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
  pkill -9 -f 'spawner' 2>/dev/null || true
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

# --- clean rebuild -----------------------------------------------------------
# A build that only succeeds incrementally is not a build.
BUILD_RC=0
BUILD_LOG="$(mktemp)"
if [ -n "$WS" ]; then
  rm -rf "$WS/build" "$WS/install" "$WS/log"
  ( cd "$WS" && colcon build --event-handlers console_direct+ ) >"$BUILD_LOG" 2>&1
  BUILD_RC=$?
  if [ -f "$WS/install/setup.bash" ]; then
    set +u
    # shellcheck disable=SC1091
    source "$WS/install/setup.bash"
    set -u
  fi
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
adopt_domain_from 'ros2_control_node'

for _ in $(seq 1 40); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *controller_manager*) break ;; esac
  sleep 1
done

# Poll: bringup returns while spawners may still be working.
HW_OUT=""
LC_OUT=""
for _ in $(seq 1 30); do
  HW_OUT="$(timeout 20 ros2 control list_hardware_components 2>&1)"
  LC_OUT="$(timeout 20 ros2 control list_controllers 2>&1)"
  if printf '%s' "$HW_OUT" | awk '/state:.*active/ {f=1} END {exit !f}' \
     && printf '%s' "$LC_OUT" | awk '/joint_state_broadcaster/ && /active/ {f=1} END {exit !f}'; then
    break
  fi
  sleep 2
done

COMPONENT_ACTIVE=false
printf '%s' "$HW_OUT" | awk '/state:.*active/ {f=1} END {exit !f}' && COMPONENT_ACTIVE=true

# The plugin must NOT be one of the shipped mock components. Read from the live
# system so any name the cell chose is accepted.
CUSTOM_PLUGIN=false
PLUGIN_NAME="$(printf '%s' "$HW_OUT" | awk -F': ' '/plugin name/ {print $2; exit}')"
if [ -n "$PLUGIN_NAME" ] \
   && ! printf '%s' "$PLUGIN_NAME" | awk '/mock_components/ {f=1} END {exit !f}'; then
  CUSTOM_PLUGIN=true
fi

JS_OUT="$(timeout 25 ros2 topic echo /joint_states --once 2>&1)"
JS_BOTH=false
if printf '%s' "$JS_OUT" | awk '/joint_a/ {a=1} /joint_b/ {b=1} END {exit !(a && b)}'; then
  JS_BOTH=true
fi

kill_all

p_builds=false;    [ "$BUILD_RC" -eq 0 ] && [ -n "$WS" ] && p_builds=true
p_custom=false;    $CUSTOM_PLUGIN && p_custom=true
p_component=false; $COMPONENT_ACTIVE && p_component=true
p_js=false;        $JS_BOTH && p_js=true

{
  printf '{\n'
  printf '  "ctl3_bringup_found": true,\n'
  printf '  "bringup": %s,\n'               "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "ws": %s,\n'                    "$(printf '%s' "${WS:--}" | json_escape)"
  printf '  "ctl3_builds": %s,\n'           "$p_builds"
  printf '  "ctl3_custom_plugin": %s,\n'    "$p_custom"
  printf '  "ctl3_component_active": %s,\n' "$p_component"
  printf '  "ctl3_joint_states": %s,\n'     "$p_js"
  printf '  "plugin_name": %s,\n'           "$(printf '%s' "${PLUGIN_NAME:--}" | json_escape)"
  printf '  "build_rc": %d,\n'              "$BUILD_RC"
  printf '  "bringup_rc": %d,\n'            "$BRING_RC"
  printf '  "hardware_components": %s,\n'   "$(printf '%s' "$HW_OUT" | head -c 900 | json_escape)"
  printf '  "list_controllers": %s,\n'      "$(printf '%s' "$LC_OUT" | head -c 600 | json_escape)"
  printf '  "build_tail": %s\n'             "$(tail -c 1200 "$BUILD_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BUILD_LOG" "$BRING_LOG"
