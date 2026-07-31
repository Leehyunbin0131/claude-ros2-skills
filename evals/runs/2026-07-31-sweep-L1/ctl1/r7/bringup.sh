#!/usr/bin/env bash
# Minimal ros2_control bringup using mock_components/GenericSystem.
# Starts robot_state_publisher, ros2_control_node, and controller spawners
# in the background, then returns.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "$SCRIPT_DIR/launch/bringup.launch.py" \
  > "$SCRIPT_DIR/bringup.log" 2>&1 &
disown

echo "ros2_control bringup started in background (log: $SCRIPT_DIR/bringup.log)"
