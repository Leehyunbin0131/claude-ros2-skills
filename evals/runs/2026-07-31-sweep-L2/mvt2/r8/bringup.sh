#!/usr/bin/env bash
# Builds (if needed) and launches the MoveIt 2 stack (robot_state_publisher,
# move_group, ros2_control_node + controller spawners) for the 3-joint "arm"
# planning group, in the background. Returns once move_group's /move_action
# action server is available.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ws"
LOG_FILE="$SCRIPT_DIR/move_group.log"

source /opt/ros/jazzy/setup.bash

if [ ! -d "$WS_DIR/install" ]; then
  echo "Building arm_moveit_config workspace..."
  ( cd "$WS_DIR" && colcon build --symlink-install )
fi

source "$WS_DIR/install/setup.bash"

: > "$LOG_FILE"
echo "Starting MoveIt stack in the background (log: $LOG_FILE)..."
nohup ros2 launch arm_moveit_config demo.launch.py >"$LOG_FILE" 2>&1 &
disown

echo "Waiting for /move_action action server to come up..."
if ! python3 - <<'PYEOF'
import sys
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from moveit_msgs.action import MoveGroup

rclpy.init()
node = Node("bringup_wait")
client = ActionClient(node, MoveGroup, "/move_action")
ok = client.wait_for_server(timeout_sec=120.0)
node.destroy_node()
rclpy.shutdown()
sys.exit(0 if ok else 1)
PYEOF
then
  echo "ERROR: move_group did not become ready in time. See $LOG_FILE" >&2
  exit 1
fi

echo "move_group is ready."
