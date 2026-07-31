#!/usr/bin/env bash
# Starts move_group (and robot_state_publisher / joint_state_publisher) in the
# background for the simple_arm MoveIt setup, then returns immediately.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

LOG_FILE="${SCRIPT_DIR}/bringup.log"
PID_FILE="${SCRIPT_DIR}/bringup.pid"

nohup ros2 launch "${SCRIPT_DIR}/launch/bringup.launch.py" \
    > "${LOG_FILE}" 2>&1 &

echo $! > "${PID_FILE}"
disown

echo "move_group bringup started in background (pid $(cat "${PID_FILE}")), logging to ${LOG_FILE}"
