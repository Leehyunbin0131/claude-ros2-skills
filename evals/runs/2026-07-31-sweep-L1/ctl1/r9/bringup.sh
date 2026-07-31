#!/usr/bin/env bash
# Minimal ros2_control bringup using mock_components/GenericSystem.
# Starts everything in the background and returns immediately.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ros2_ws"

source /opt/ros/jazzy/setup.bash
source "$WS_DIR/install/setup.bash"

nohup ros2 launch minimal_control_demo bringup.launch.py \
    > /tmp/minimal_control_demo_bringup.log 2>&1 &
disown

# Give the controller manager & spawners time to come up.
sleep 8
