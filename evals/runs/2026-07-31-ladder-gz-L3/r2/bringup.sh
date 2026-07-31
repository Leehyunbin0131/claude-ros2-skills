#!/usr/bin/env bash
# Starts Gazebo, spawns the robot, and bridges the IMU/clock topics into ROS 2,
# all in the background. Returns immediately; nothing here is cleaned up.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v ros2 >/dev/null 2>&1; then
    source /opt/ros/jazzy/setup.bash
fi

nohup ros2 launch "$DIR/bringup.launch.py" > "$DIR/bringup.log" 2>&1 &
disown

echo "bringup started in background (pid $!); logs at $DIR/bringup.log"
