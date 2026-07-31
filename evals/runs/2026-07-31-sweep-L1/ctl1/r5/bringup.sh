#!/usr/bin/env bash
# Build and launch a minimal ros2_control demo (mock_components/GenericSystem)
# with two revolute joints (joint_a, joint_b) in the background.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source /opt/ros/jazzy/setup.bash

colcon build --packages-select minimal_control_demo

source install/setup.bash

nohup ros2 launch minimal_control_demo bringup.launch.py \
    > /tmp/minimal_control_demo_bringup.log 2>&1 &
disown

echo "bringup launched in background (PID $!). Log: /tmp/minimal_control_demo_bringup.log"
