#!/usr/bin/env bash
# Real-outcome checks for the ros2-control ladder, rung L2.
#
#   ./ctl2_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   a second controller loaded and claiming interfaces -> ctl2_both_active
#   a command actually reaching the mocked hardware    -> ctl2_command_lands
#
# `ctl2_command_lands` is the rung. A `forward_command_controller` can be
# active while its `joints` / `interface_name` parameters are wrong or its
# command topic is something else entirely: everything reports healthy,
# `list_controllers` shows two active controllers, and the commanded position
# never appears in `/joint_states`. So the check publishes a real command and
# reads the state back, rather than trusting the controller list.
#
# The command topic is DISCOVERED, not assumed. `forward_command_controller`
# publishes on `<controller_name>/commands`, but the prompt lets the cell name
# the controller `position_controller` and nothing forces a particular
# namespace, so asserting a hardcoded topic would fail correct work. Any
# `std_msgs/msg/Float64MultiArray` subscription on the graph is accepted.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * controller_manager IGNORES SIGTERM -- kill -9, and never `wait` on it
#   * ROS_DOMAIN_ID isolation, so a stray node cannot answer for the cell
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: ctl2_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: ctl2_check.sh <cell-workdir> <out.json>}"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"ctl2_bringup_found": false}\n' > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'ros2_control_node' 2>/dev/null || true
  pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
  pkill -9 -f 'spawner' 2>/dev/null || true
  pkill -9 -f '^python3 .*ctl2_probe' 2>/dev/null || true
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
( cd "$BDIR" && timeout 150 bash ./bringup.sh ) >"$BRING_LOG" 2>&1
BRING_RC=$?

# The cell's bringup may set its own ROS_DOMAIN_ID. That is CORRECT practice --
# it isolates the system from stray nodes left by other sessions -- and it is
# invisible to us unless we ask. Two L2 cells did exactly that (one derived from
# a directory hash, one a literal 77) and were the only two scored as total
# failures, because this checker went on querying its own domain and saw
# nothing. Read the domain back off a process the bringup actually started.
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

# Poll rather than sample once. `bringup.sh` "starts everything in the
# background and returns", so a spawner may still be working when it does --
# and one L2 cell was scored 1 active controller here while its command landed
# correctly a few seconds later, which is a contradiction produced entirely by
# reading the list too early.
LC_OUT=""
N_ACTIVE=0
for _ in $(seq 1 30); do
  LC_OUT="$(timeout 20 ros2 control list_controllers 2>&1)"
  N_ACTIVE=$(printf '%s' "$LC_OUT" | awk '/active/ {n++} END {print n+0}')
  [ "${N_ACTIVE:-0}" -ge 2 ] && break
  sleep 2
done
BOTH_ACTIVE=false
[ "${N_ACTIVE:-0}" -ge 2 ] && BOTH_ACTIVE=true

# Publish the command and read the state back. Both the topic discovery and
# the readback happen in one node so the publisher stays alive while the
# controller runs -- a publisher that exits immediately can be dropped before
# the controller's update cycle sees it.
PROBE_OUT="$(timeout 90 python3 - <<'PYEOF' 2>&1
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

TARGET = {"joint_a": 0.5, "joint_b": -0.5}
TOL = 0.05

rclpy.init()
node = Node("ctl2_probe")

# Discover the command topic by TYPE, not by name: the prompt does not fix a
# namespace, so a hardcoded topic would fail correct work.
topic = None
deadline = time.time() + 20.0
while time.time() < deadline and topic is None:
    for name, types in node.get_topic_names_and_types():
        if "std_msgs/msg/Float64MultiArray" in types:
            topic = name
            break
    if topic is None:
        rclpy.spin_once(node, timeout_sec=0.5)

if topic is None:
    print("NO_COMMAND_TOPIC")
    sys.exit(0)
print(f"COMMAND_TOPIC {topic}")

pub = node.create_publisher(Float64MultiArray, topic, 10)
latest = {}


def on_js(msg):
    for n, p in zip(msg.name, msg.position):
        latest[n] = p


node.create_subscription(JointState, "/joint_states", on_js, 10)

msg = Float64MultiArray()
msg.data = [0.5, -0.5]

ok = False
deadline = time.time() + 30.0
while time.time() < deadline:
    pub.publish(msg)
    rclpy.spin_once(node, timeout_sec=0.2)
    if all(abs(latest.get(j, 1e9) - v) < TOL for j, v in TARGET.items()):
        ok = True
        break

print("STATE " + " ".join(f"{k}={v:.3f}" for k, v in sorted(latest.items())))
print("LANDED" if ok else "NOT_LANDED")
PYEOF
)"

CMD_LANDS=false
if printf '%s' "$PROBE_OUT" | awk '/^LANDED$/ {found=1} END {exit !found}'; then
  CMD_LANDS=true
fi

kill_all

p_both=false;  $BOTH_ACTIVE && p_both=true
p_cmd=false;   $CMD_LANDS && p_cmd=true

{
  printf '{\n'
  printf '  "ctl2_bringup_found": true,\n'
  printf '  "bringup": %s,\n'             "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "ctl2_both_active": %s,\n'    "$p_both"
  printf '  "ctl2_command_lands": %s,\n'  "$p_cmd"
  printf '  "n_active": %d,\n'            "${N_ACTIVE:-0}"
  printf '  "bringup_rc": %d,\n'          "$BRING_RC"
  printf '  "list_controllers": %s,\n'    "$(printf '%s' "$LC_OUT" | head -c 800 | json_escape)"
  printf '  "probe": %s,\n'               "$(printf '%s' "$PROBE_OUT" | head -c 800 | json_escape)"
  printf '  "bringup_tail": %s\n'         "$(tail -c 1200 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG"
