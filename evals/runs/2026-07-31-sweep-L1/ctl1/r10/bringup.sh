#!/bin/bash
# Builds (if needed) and launches the minimal ros2_control mock-hardware demo
# in the background, then returns immediately.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

source /opt/ros/jazzy/setup.bash

if [ ! -d install ]; then
  colcon build --symlink-install
fi

source install/setup.bash

nohup ros2 launch mini_control_demo bringup.launch.py \
  > "$SCRIPT_DIR/bringup.log" 2>&1 &
disown

echo "mini_control_demo bringup started in background (PID $!)."
echo "Logs: $SCRIPT_DIR/bringup.log"
