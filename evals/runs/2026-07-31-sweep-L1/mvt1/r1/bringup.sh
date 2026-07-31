#!/bin/bash
# Starts move_group (and its supporting nodes) for the simple 3-joint arm
# MoveIt setup, in the background, then returns immediately.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/launch/move_group.launch.py" \
    > "${SCRIPT_DIR}/move_group.log" 2>&1 &
disown

echo "move_group launching in background (pid $!), logging to ${SCRIPT_DIR}/move_group.log"
