#!/usr/bin/env bash
# Starts robot_state_publisher, joint_state_publisher and move_group (MoveIt 2)
# for the simple 3-joint "arm" planning group, in the background, then returns.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/.bringup"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

set -u

# This host may run multiple, unrelated ROS 2 sessions at once and everyone
# defaults to ROS_DOMAIN_ID=0. Pick a random private domain so our graph
# doesn't collide/interfere with others, and persist it so plan.py (run
# later, in a fresh shell) can pick up the same value.
DOMAIN_ID=$(( (RANDOM % 200) + 1 ))
export ROS_DOMAIN_ID="$DOMAIN_ID"
echo "$DOMAIN_ID" > "$LOG_DIR/ros_domain_id"

# The loopback interface on this host has multicast disabled, which breaks
# Fast-DDS's default multicast-based discovery (nodes never find each other,
# even on localhost). Force discovery over unicast to localhost instead.
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS=127.0.0.1

# Launch move_group (and the nodes it depends on) fully detached so it
# keeps running after this script exits.
nohup ros2 launch "$SCRIPT_DIR/launch/move_group.launch.py" \
    > "$LOG_DIR/move_group.log" 2>&1 &
LAUNCH_PID=$!
disown "$LAUNCH_PID"
echo "$LAUNCH_PID" > "$LOG_DIR/move_group.pid"

echo "Started move_group bringup in background (launch pid $LAUNCH_PID, ROS_DOMAIN_ID=$DOMAIN_ID)."
echo "Logs: $LOG_DIR/move_group.log"

# Wait until the move_group action server is actually reachable before
# returning, so callers can immediately use plan.py. This uses the same
# action-client mechanism plan.py uses, in a single long-lived node, which is
# more reliable than repeatedly shelling out to `ros2 action list`.
python3 - <<'PYEOF'
import sys
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from moveit_msgs.action import MoveGroup

rclpy.init()
node = Node("bringup_ready_check")
client = ActionClient(node, MoveGroup, "/move_action")
ok = client.wait_for_server(timeout_sec=60.0)
node.destroy_node()
rclpy.shutdown()
sys.exit(0 if ok else 1)
PYEOF
READY=$?

if [ "$READY" -eq 0 ]; then
    echo "move_group is up (/move_action action server available)."
    exit 0
else
    echo "Timed out waiting for move_group to become ready; check $LOG_DIR/move_group.log" >&2
    exit 1
fi
