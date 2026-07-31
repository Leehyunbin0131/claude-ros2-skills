#!/usr/bin/env bash
# Minimal ros2_control bringup using mock_components/GenericSystem.
# Starts everything in the background and returns immediately.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/launch/mock_robot.launch.py" \
    > "${SCRIPT_DIR}/bringup.log" 2>&1 &
disown

echo "ros2_control mock bringup launched in background (PID $!)."
echo "Logs: ${SCRIPT_DIR}/bringup.log"
