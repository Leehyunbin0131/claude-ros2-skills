#!/usr/bin/env bash
# Starts move_group (and its supporting nodes) in the background for the
# three_link_arm MoveIt 2 setup, then returns immediately.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/launch/move_group.launch.py" \
    > "${SCRIPT_DIR}/bringup.log" 2>&1 &
disown

echo "move_group bringup launched in background (PID $!). Logs: ${SCRIPT_DIR}/bringup.log"
