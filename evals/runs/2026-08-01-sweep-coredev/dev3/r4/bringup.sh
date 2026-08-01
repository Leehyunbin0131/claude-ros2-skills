#!/usr/bin/env bash
# Starts the Nav2 navigation stack in the background and returns immediately.
# Assumes /scan (sensor_msgs/msg/LaserScan, frame_id=laser_frame) is being
# published and that map -> odom -> base_link -> laser_frame TF is already
# being broadcast by another process.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/nav2_bringup_launch.py" \
  params_file:="${SCRIPT_DIR}/nav2_params.yaml" \
  use_sim_time:=false \
  > "${SCRIPT_DIR}/nav2_bringup.log" 2>&1 &

disown

echo "Nav2 stack starting in background (PID $!). Logs: ${SCRIPT_DIR}/nav2_bringup.log"
