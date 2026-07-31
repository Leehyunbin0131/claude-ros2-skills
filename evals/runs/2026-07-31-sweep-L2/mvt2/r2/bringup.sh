#!/usr/bin/env bash
# Starts robot_state_publisher, joint_state_publisher and move_group in the
# background for the arm3 MoveIt setup, waits until move_group's action
# server is actually up, then returns (the nodes keep running detached).
set -o pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

PID_FILE="$DIR/.bringup_pids"
: > "$PID_FILE"

setsid ros2 launch "$DIR/launch/bringup_launch.py" \
    > "$LOG_DIR/bringup.log" 2>&1 < /dev/null &
LAUNCH_PID=$!
disown "$LAUNCH_PID"
echo "$LAUNCH_PID" >> "$PID_FILE"

echo "Launched ros2 launch (pid $LAUNCH_PID), waiting for move_group action server..."

python3 - "$DIR" <<'EOF'
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from moveit_msgs.action import MoveGroup

rclpy.init(args=None)
node = Node("bringup_wait_for_move_group")
client = ActionClient(node, MoveGroup, "move_action")

deadline = time.time() + 60.0
ready = False
while time.time() < deadline:
    if client.wait_for_server(timeout_sec=1.0):
        ready = True
        break
    rclpy.spin_once(node, timeout_sec=0.1)

node.destroy_node()
rclpy.shutdown()

if not ready:
    print("Timed out waiting for /move_group action server", file=sys.stderr)
    sys.exit(1)

print("move_group action server is up.")
EOF
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
    echo "bringup.sh: move_group did not come up in time, see $LOG_DIR/bringup.log" >&2
    tail -n 60 "$LOG_DIR/bringup.log" >&2 || true
    exit 1
fi

echo "bringup.sh: MoveIt bringup complete (move_group ready)."
exit 0
