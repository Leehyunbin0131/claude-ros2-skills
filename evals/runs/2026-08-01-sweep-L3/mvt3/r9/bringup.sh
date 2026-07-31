#!/usr/bin/env bash
# Starts move_group (and everything it needs: robot_state_publisher, a
# joint_states source) in the background for the simple_arm MoveIt 2 setup,
# waits until move_group is actually ready to accept planning requests, then
# returns control to the caller. The launched processes keep running
# detached from this shell (nohup + disown).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

nohup ros2 launch "$SCRIPT_DIR/bringup_launch.py" \
    > "$LOG_DIR/bringup.log" 2>&1 &
LAUNCH_PID=$!
disown

echo "Launched MoveIt bringup (pid $LAUNCH_PID), log: $LOG_DIR/bringup.log"
echo "Waiting for move_group action server to come up..."

python3 - <<'PYEOF'
import sys
import rclpy
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup

rclpy.init()
node = rclpy.create_node("bringup_wait")
client = ActionClient(node, MoveGroup, "move_action")
ready = client.wait_for_server(timeout_sec=90.0)
node.destroy_node()
rclpy.shutdown()
sys.exit(0 if ready else 1)
PYEOF
WAIT_STATUS=$?

if [ "$WAIT_STATUS" -ne 0 ]; then
    echo "ERROR: move_group did not become ready in time. Check $LOG_DIR/bringup.log" >&2
    exit 1
fi

echo "move_group is up and ready."
exit 0
