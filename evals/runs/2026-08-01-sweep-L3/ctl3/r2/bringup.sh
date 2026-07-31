#!/bin/bash
# Starts the my_hw ros2_control stack in the background and returns immediately.
# Does not wait for anything to become ready and does not clean up after itself.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/ws"
LOG_FILE="/tmp/my_hw_bringup.log"

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

nohup ros2 launch my_hw bringup.launch.py > "${LOG_FILE}" 2>&1 < /dev/null &
disown

echo "my_hw bringup launched in background (pid $!), logging to ${LOG_FILE}"
