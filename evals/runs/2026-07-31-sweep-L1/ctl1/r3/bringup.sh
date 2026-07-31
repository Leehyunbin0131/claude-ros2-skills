#!/usr/bin/env bash
# Bring up a minimal mock_components/GenericSystem ros2_control system
# (joint_a, joint_b) in the background and return immediately.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "$SCRIPT_DIR/launch/bringup.launch.py" \
    > "$SCRIPT_DIR/bringup.log" 2>&1 &
disown

echo "ros2_control mock system launching in background (PID $!)."
echo "Logs: $SCRIPT_DIR/bringup.log"
