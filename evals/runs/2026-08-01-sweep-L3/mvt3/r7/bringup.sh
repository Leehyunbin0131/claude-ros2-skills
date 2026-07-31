#!/usr/bin/env bash
# Starts move_group (plus robot_state_publisher and joint_state_publisher) for
# the simple 3-joint arm in the background, waits until the move_group action
# server is reachable, then returns.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

LOG="$DIR/move_group.log"
PIDFILE="$DIR/.bringup.pid"

setsid nohup ros2 launch "$DIR/launch/bringup_launch.py" > "$LOG" 2>&1 < /dev/null &
echo $! > "$PIDFILE"
disown

echo "MoveIt bringup started in background (PID $(cat "$PIDFILE")). Logs: $LOG"

# Wait (bounded) for the move_group action server to be reachable so that a
# subsequent plan.py invocation can succeed immediately.
python3 - <<'EOF'
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup

rclpy.init()
node = Node("bringup_wait")
client = ActionClient(node, MoveGroup, "/move_action")

deadline = time.time() + 60.0
ready = False
while time.time() < deadline:
    if client.wait_for_server(timeout_sec=1.0):
        ready = True
        break

node.destroy_node()
rclpy.shutdown()
sys.exit(0 if ready else 1)
EOF
WAIT_STATUS=$?

if [ "$WAIT_STATUS" -ne 0 ]; then
  echo "WARNING: move_group action server did not come up within timeout, check $LOG" >&2
else
  echo "move_group is up."
fi

exit 0
