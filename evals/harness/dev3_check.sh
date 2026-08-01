#!/usr/bin/env bash
# Real-outcome checks for the ros2-dev ladder, rung L3.
#
#   ./dev3_check.sh <cell-workdir> <out.json>
#
# Mechanisms and the check that catches each:
#
#   the local costmap actually published      -> dev3_costmap_published
#   live scan data marked as obstacles in it  -> dev3_obstacle_marked
#
# There was a third check, `dev3_controller_active`, and it was WRONG: the
# frozen prompt asks for `/local_costmap/costmap` to be published with a cell
# above 250 and never mentions a controller_server. Two cells brought up a
# standalone nav2_costmap_2d node instead of a controller -- which satisfies
# everything the task asks -- and were scored as failures for it, marking 12 and
# 325 lethal cells while doing so. Recorded rather than quietly dropped: this
# checker asserted something the prompt does not require, which is the one rule
# every header in this harness repeats.
#
# `dev3_obstacle_marked` is the rung. A costmap can be configured, active and
# publishing while its obstacle layer has no observation source wired: the map
# is all zeros, every node reports healthy, and only the cell values say so.
# The scenario puts a solid return at 1.0 m in a 30-degree arc dead ahead, so a
# correctly wired costmap has unambiguous lethal cells to show.
#
# The scenario runs HERE, on this checker's own ROS_DOMAIN_ID: one started by
# run_ab.sh for the cell is on a different domain and invisible.
#
# Traps this file is written downstream of, each paid for in an earlier round:
#   * no `cmd | grep -q X` -- `set -o pipefail` turns a match into a failure
#   * no `grep -c` for counting -- prints 0 AND exits 1. awk instead.
#   * `/active/` also matches `inactive` -- compare the first field exactly
#   * the cell may set its own ROS_DOMAIN_ID (correct practice) -- adopt it
#   * kill the `ros2 launch` wrapper too, or a re-entrancy guard skips relaunch
#   * `pkill -f "$BDIR"` matches this checker's own command line -- exclude self
#   * bounded wait loops, so a verdict always gets written
#   * assert nothing the frozen prompt does not require
set -uo pipefail

WORK="${1:?usage: dev3_check.sh <cell-workdir> <out.json>}"
OUT="${2:?usage: dev3_check.sh <cell-workdir> <out.json>}"
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

BRINGUP="$(find "$WORK" -maxdepth 3 -name 'bringup.sh' -print -quit 2>/dev/null)"
if [ -z "$BRINGUP" ]; then
  printf '{"dev3_bringup_found": false}\n' > "$OUT"
  exit 0
fi
BDIR="$(dirname "$BRINGUP")"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$(( 30 + RANDOM % 60 ))

kill_all() {
  pkill -9 -f 'controller_server' 2>/dev/null || true
  pkill -9 -f 'planner_server' 2>/dev/null || true
  pkill -9 -f 'behavior_server' 2>/dev/null || true
  pkill -9 -f 'bt_navigator' 2>/dev/null || true
  pkill -9 -f 'lifecycle_manager' 2>/dev/null || true
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

bash "$HARNESS/dev3_scenario.sh" up >/dev/null 2>&1 &
SCENARIO=$!
for _ in $(seq 1 25); do
  TL="$(timeout 5 ros2 topic list 2>/dev/null || true)"
  case "$TL" in */scan*) break ;; esac
  sleep 1
done

BRING_LOG="$(mktemp)"
( cd "$BDIR" && timeout 240 bash ./bringup.sh ) >"$BRING_LOG" 2>&1
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
adopt_domain_from 'controller_server'

# Recorded for diagnosis only, never scored: a cell may reach the costmap
# through a controller_server or through a standalone costmap node.
CS_STATE="-"
for _ in $(seq 1 10); do
  CS_STATE="$(timeout 5 ros2 lifecycle get /controller_server 2>&1 | head -1)"
  printf '%s' "$CS_STATE" | awk '$1=="active" {f=1} END {exit !f}' && break
  sleep 2
done

# Read the costmap and look for lethal cells. Discovered by TYPE so the exact
# topic name the cell chose is not asserted.
COSTMAP_OUT="$(timeout 90 python3 - <<'PYEOF' 2>&1
import sys
import time

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

rclpy.init()
node = Node("costmap_probe")

topic = None
deadline = time.time() + 25.0
while time.time() < deadline and topic is None:
    for name, types in node.get_topic_names_and_types():
        if "nav_msgs/msg/OccupancyGrid" in types and "costmap" in name:
            topic = name
            break
    if topic is None:
        rclpy.spin_once(node, timeout_sec=0.5)

if topic is None:
    print("NO_COSTMAP_TOPIC")
    sys.exit(0)
print(f"COSTMAP_TOPIC {topic}")

best = {"n": 0, "hi": 0}


def cb(msg):
    hi = max((v for v in msg.data), default=0)
    lethal = sum(1 for v in msg.data if v > 250 or v == 100)
    if lethal > best["n"]:
        best["n"] = lethal
    if hi > best["hi"]:
        best["hi"] = hi


# Costmaps are published transient_local; accept either durability.
for dur in (DurabilityPolicy.TRANSIENT_LOCAL, DurabilityPolicy.VOLATILE):
    node.create_subscription(
        OccupancyGrid, topic, cb,
        QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE, durability=dur))

got = 0
deadline = time.time() + 40.0
while time.time() < deadline:
    rclpy.spin_once(node, timeout_sec=0.5)
    if best["hi"] > 0:
        got += 1
        if got > 3:
            break

print(f"LETHAL {best['n']} MAXCOST {best['hi']}")
PYEOF
)"

COSTMAP_PUB=false
printf '%s' "$COSTMAP_OUT" | awk '/^COSTMAP_TOPIC/ {f=1} END {exit !f}' && COSTMAP_PUB=true

N_LETHAL=$(printf '%s' "$COSTMAP_OUT" | awk '/^LETHAL/ {print $2; exit}')
MAXCOST=$(printf '%s' "$COSTMAP_OUT" | awk '/^LETHAL/ {print $4; exit}')
OBSTACLE=false
[ -n "${N_LETHAL:-}" ] && [ "${N_LETHAL:-0}" -ge 1 ] && OBSTACLE=true

kill_all
kill -9 $SCENARIO 2>/dev/null || true
pkill -9 -f 'dev3_scenario' 2>/dev/null || true

p_costmap=false;  $COSTMAP_PUB && p_costmap=true
p_obstacle=false; $OBSTACLE && p_obstacle=true

{
  printf '{\n'
  printf '  "dev3_bringup_found": true,\n'
  printf '  "bringup": %s,\n'                  "$(printf '%s' "$BRINGUP" | json_escape)"
  printf '  "dev3_costmap_published": %s,\n'   "$p_costmap"
  printf '  "dev3_obstacle_marked": %s,\n'     "$p_obstacle"
  printf '  "cs_state_unscored": %s,\n'        "$(printf '%s' "$CS_STATE" | json_escape)"
  printf '  "n_lethal": %d,\n'                 "${N_LETHAL:-0}"
  printf '  "max_cost": %d,\n'                 "${MAXCOST:-0}"
  printf '  "costmap_probe": %s,\n'            "$(printf '%s' "$COSTMAP_OUT" | head -c 500 | json_escape)"
  printf '  "bringup_rc": %d,\n'               "$BRING_RC"
  printf '  "bringup_tail": %s\n'              "$(tail -c 1200 "$BRING_LOG" | json_escape)"
  printf '}\n'
} > "$OUT"
rm -f "$BRING_LOG"
