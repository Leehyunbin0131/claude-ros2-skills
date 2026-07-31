#!/usr/bin/env bash
# Real-outcome checks for the ros2-moveit ladder, rung L1.
#
#   ./mvt1_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a self-authored URDF + matching SRDF with group `arm`  -> mvt1_group_known
#   move_group actually reaching a usable state            -> mvt1_move_group_up
#   its planning service being offered                     -> mvt1_plan_service
#
# `mvt1_move_group_up` alone is not enough. move_group appears in `ros2 node
# list` well before it has loaded a robot model, and a setup whose SRDF never
# reached it still shows the node. `mvt1_group_known` is the one that separates
# "the process is running" from "MoveIt has a planning group called arm":
# it reads the group names move_group itself reports, so an SRDF that was
# written but never passed to the node fails it.
#
# Graded by RUNNING the cell's bringup.sh and then querying the live system.
# Nothing reads the source: a launch file, MoveItConfigsBuilder, or raw node
# invocations are equally correct.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * kill -9, never `wait` on a child that may ignore SIGTERM
#   * ROS_DOMAIN_ID isolation, so a stray node from another round cannot answer
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: mvt1_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: mvt1_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"mvt1_bringup_found": false}\n' > "$OUT"
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
  pkill -9 -f '^python3 .*bringup' 2>/dev/null || true
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

MG_UP=false
for _ in $(seq 1 60); do
  NL="$(timeout 5 ros2 node list 2>/dev/null || true)"
  case "$NL" in *move_group*) MG_UP=true; break ;; esac
  sleep 1
done

# Bounded so the three wait loops cannot together exceed the caller's timeout:
# 60 s for the node + 30 s for the service + 30 s for the probe. An earlier
# version could spend 240 s here alone and was killed before writing out.json.
SVC_OUT=""
PLAN_SVC=false
for _ in $(seq 1 15); do
  SVC_OUT="$(timeout 4 ros2 service list 2>/dev/null || true)"
  case "$SVC_OUT" in *plan_kinematic_path*) PLAN_SVC=true; break ;; esac
  sleep 1
done

# Ask move_group which planning groups it actually loaded. This is the check
# that a written-but-unwired SRDF cannot pass.
GROUPS_OUT="$(timeout 30 python3 - <<'PYEOF' 2>&1
import sys
import rclpy
from rclpy.node import Node

try:
    from moveit_msgs.srv import GetPlanningSceneComponents  # noqa: F401
except Exception:
    pass

rclpy.init()
node = Node("group_probe")
# The robot model reaches every MoveIt client through these two parameters on
# move_group; reading them back is the least intrusive way to see what it has.
from rcl_interfaces.srv import GetParameters
cli = node.create_client(GetParameters, "/move_group/get_parameters")
if not cli.wait_for_service(timeout_sec=15.0):
    print("NO_PARAM_SERVICE")
    sys.exit(0)
req = GetParameters.Request()
req.names = ["robot_description_semantic"]
fut = cli.call_async(req)
rclpy.spin_until_future_complete(node, fut, timeout_sec=15.0)
res = fut.result()
if res is None or not res.values:
    print("NO_VALUE")
    sys.exit(0)
srdf = res.values[0].string_value or ""
import re
names = re.findall(r'<group\s+name="([^"]+)"', srdf)
print("GROUPS " + ",".join(names) if names else "GROUPS_EMPTY")
PYEOF
)"

GROUP_KNOWN=false
if printf '%s' "$GROUPS_OUT" | awk '/^GROUPS / && /arm/ {found=1} END {exit !found}'; then
  GROUP_KNOWN=true
fi

kill_all

p_mg=false;    $MG_UP && p_mg=true
p_svc=false;   $PLAN_SVC && p_svc=true
p_group=false; $GROUP_KNOWN && p_group=true

{
  printf '{\n'
  printf '  "mvt1_bringup_found": true,\n'
  printf '  "bringup": %s,\n'             "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "mvt1_move_group_up": %s,\n'  "$p_mg"
  printf '  "mvt1_plan_service": %s,\n'   "$p_svc"
  printf '  "mvt1_group_known": %s,\n'    "$p_group"
  printf '  "bringup_rc": %d,\n'          "$BRING_RC"
  printf '  "groups_probe": %s,\n'        "$(printf '%s' "$GROUPS_OUT" | head -c 500 | json_escape)"
  printf '  "bringup_tail": %s\n'         "$(tail -c 1500 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG"
