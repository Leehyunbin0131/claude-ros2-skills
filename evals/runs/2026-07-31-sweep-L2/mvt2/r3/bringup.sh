#!/usr/bin/env bash
# Starts move_group (and everything it needs: robot_state_publisher,
# ros2_control_node, controller spawners) in the background for the
# simple 3-joint "arm" MoveIt setup, then returns once the move_group
# action server is available.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/.log"
mkdir -p "${LOG_DIR}"

# ROS 2's setup.bash references unset variables, so it is not compatible
# with `set -u`.
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/launch/move_group.launch.py" \
    > "${LOG_DIR}/bringup.log" 2>&1 &
LAUNCH_PID=$!
echo "${LAUNCH_PID}" > "${LOG_DIR}/bringup.pid"
disown "${LAUNCH_PID}" 2>/dev/null || true

echo "Launched move_group stack in background (pid ${LAUNCH_PID}), logs at ${LOG_DIR}/bringup.log"

# Wait for the /move_action action server to come up before returning so
# callers (e.g. plan.py) can immediately request a plan.
TIMEOUT=60
python3 - "$TIMEOUT" <<'EOF'
import sys
import rclpy
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup

timeout = float(sys.argv[1])
rclpy.init()
node = rclpy.create_node("bringup_wait_for_move_group")
client = ActionClient(node, MoveGroup, "/move_action")
ready = client.wait_for_server(timeout_sec=timeout)
node.destroy_node()
rclpy.shutdown()
if not ready:
    print("ERROR: /move_action action server did not come up in time", file=sys.stderr)
    sys.exit(1)
print("move_group is ready (/move_action action server is up)")
EOF
