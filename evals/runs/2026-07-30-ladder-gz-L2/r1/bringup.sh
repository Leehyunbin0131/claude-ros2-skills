#!/usr/bin/env bash
# Brings up a Gazebo Harmonic world with a diff-drive robot + 360-sample GPU
# lidar, and bridges /clock, /scan, /cmd_vel to ROS 2 Jazzy. Starts everything
# in the background and returns immediately; does not clean up.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/log"
mkdir -p "${LOG_DIR}"

source /opt/ros/jazzy/setup.bash

# This sandbox has no accessible GPU/DRI device, so force Ogre2 to use the
# llvmpipe software rasterizer over the existing X display rather than the
# EGL headless device path (which fails with "Permission denied" on
# /dev/dri/card0).
export LIBGL_ALWAYS_SOFTWARE=1
export DISPLAY="${DISPLAY:-:0}"

cd "${SCRIPT_DIR}"

nohup gz sim -s -r diffbot_world.sdf \
  > "${LOG_DIR}/gz_sim.log" 2>&1 &
disown

# Give the gz-transport master a moment to come up before the bridge
# connects to it.
sleep 5

nohup ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:="${SCRIPT_DIR}/bridge_config.yaml" -p use_sim_time:=true \
  > "${LOG_DIR}/ros_gz_bridge.log" 2>&1 &
disown

echo "Bringup launched. Logs in ${LOG_DIR}/"
echo "  gz sim:          ${LOG_DIR}/gz_sim.log"
echo "  ros_gz_bridge:   ${LOG_DIR}/ros_gz_bridge.log"
