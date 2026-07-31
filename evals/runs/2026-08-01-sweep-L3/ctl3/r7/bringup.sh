#!/usr/bin/env bash
# Starts the my_hw ros2_control demo in the background and returns immediately.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/ws"

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

nohup ros2 launch my_hw bringup.launch.py > /tmp/my_hw_bringup.log 2>&1 &
disown

echo "my_hw bringup launched in background (log: /tmp/my_hw_bringup.log)"
