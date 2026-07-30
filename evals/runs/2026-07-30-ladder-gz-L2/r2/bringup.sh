#!/usr/bin/env bash
# Brings up Gazebo Harmonic + the diff-drive/GPU-lidar world, and bridges
# /scan, /clock, /cmd_vel to ROS 2 Jazzy. Starts everything in the
# background and returns; nothing here is cleaned up automatically.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

mkdir -p "${SCRIPT_DIR}/logs"

# WSLg exposes a working X11 display but not /dev/dri render nodes, so
# --headless-rendering (which requires direct DRI access) segfaults here.
# Rendering (needed for the GPU lidar) works fine through GLX via $DISPLAY.
export DISPLAY="${DISPLAY:-:0}"

nohup gz sim -s -r -v 3 "${SCRIPT_DIR}/worlds/diff_drive_world.sdf" \
  > "${SCRIPT_DIR}/logs/gz_sim.log" 2>&1 &
disown

# Give the simulator a moment to come up and advertise its gz topics
# before the bridge tries to match them.
sleep 8

nohup ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:="${SCRIPT_DIR}/config/ros_gz_bridge.yaml" \
  -p use_sim_time:=true \
  > "${SCRIPT_DIR}/logs/ros_gz_bridge.log" 2>&1 &
disown

echo "Gazebo + ROS 2 bridge starting in background."
echo "Logs: ${SCRIPT_DIR}/logs/gz_sim.log , ${SCRIPT_DIR}/logs/ros_gz_bridge.log"
