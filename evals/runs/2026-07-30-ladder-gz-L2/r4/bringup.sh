#!/usr/bin/env bash
# Brings up a Gazebo Harmonic world with a differential-drive robot + GPU
# lidar, and bridges /clock, /cmd_vel, /scan to ROS 2. Starts everything in
# the background and returns immediately; nothing is cleaned up here.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="$SCRIPT_DIR/diffbot_world.sdf"
LOG_DIR="$SCRIPT_DIR/.bringup_logs"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

nohup gz sim -s -r --headless-rendering -v 3 "$WORLD_FILE" \
  > "$LOG_DIR/gz_sim.log" 2>&1 &
disown

sleep 5

nohup ros2 run ros_gz_bridge parameter_bridge \
  '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' \
  '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist' \
  '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan' \
  --ros-args -p use_sim_time:=true \
  > "$LOG_DIR/ros_gz_bridge.log" 2>&1 &
disown

echo "Bringup launched. Logs in $LOG_DIR"
