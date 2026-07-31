#!/usr/bin/env bash
# Starts the my_hw ros2_control bringup (controller_manager + hardware plugin +
# joint_state_broadcaster + joint_trajectory_controller) in the background and
# returns immediately. Logs go to /tmp/my_hw_bringup.log.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/ros2_ws"
LOG_FILE="/tmp/my_hw_bringup.log"

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

nohup ros2 launch my_hw bringup.launch.py > "${LOG_FILE}" 2>&1 &
disown

echo "my_hw bringup launched in background (PID $!). Logs: ${LOG_FILE}"
