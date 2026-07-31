#!/usr/bin/env bash
# Starts move_group (plus robot_state_publisher and joint_state_publisher) for the
# 3-joint "arm" MoveIt setup, in the background. Does not wait or clean up.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

mkdir -p "${SCRIPT_DIR}/log"

nohup ros2 launch "${SCRIPT_DIR}/launch/bringup.launch.py" \
    > "${SCRIPT_DIR}/log/bringup.log" 2>&1 &

disown

echo "MoveIt bringup launched in background (PID $!). Logs: ${SCRIPT_DIR}/log/bringup.log"
