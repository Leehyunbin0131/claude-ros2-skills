#!/usr/bin/env bash
# Starts the my_hw ros2_control demo (controller_manager, robot_state_publisher,
# joint_state_broadcaster and position_controller) in the background and returns.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/ros2_ws"

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

nohup ros2 launch my_hw bringup.launch.py > /tmp/my_hw_bringup.log 2>&1 &
disown

echo "my_hw bringup launched in background (log: /tmp/my_hw_bringup.log)"
