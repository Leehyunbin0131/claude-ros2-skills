#!/usr/bin/env bash
# Starts Gazebo Harmonic (server-only) with the diff-drive + GPU lidar
# world, plus the ros_gz_bridge topics needed to drive/read it from ROS 2.
# Everything is launched in the background; this script returns
# immediately and does not wait for or clean up the processes.
#
# Both gz sim and the bridge are run under a small respawn loop: this
# sandbox is a shared, occasionally unstable host (observed random
# SIGSEGVs hitting unrelated processes), so if either process dies it is
# restarted automatically to keep /scan, /clock and /cmd_vel available.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="${SCRIPT_DIR}/diff_drive_lidar.sdf"
BRIDGE_CONFIG="${SCRIPT_DIR}/bridge.yaml"
LOG_DIR="${SCRIPT_DIR}/log"
mkdir -p "${LOG_DIR}"

source /opt/ros/jazzy/setup.bash

export GZ_SIM_RESOURCE_PATH="${SCRIPT_DIR}:${GZ_SIM_RESOURCE_PATH}"
# This sandbox has no usable /dev/dri access, so EGL headless rendering
# (--headless-rendering) fails to create a GL context. There is, however,
# a working X server (WSLg) already listening on :0 that provides a
# usable GLX context, which is what the GPU lidar sensor needs to render.
# Route through that instead of headless EGL.
export DISPLAY="${DISPLAY:-:0}"

nohup bash -c "
  while true; do
    gz sim -s -r -v 3 '${WORLD_FILE}'
    echo '--- gz sim exited, restarting in 2s ---'
    sleep 2
  done
" > "${LOG_DIR}/gz_sim.log" 2>&1 &
disown

nohup bash -c "
  while true; do
    ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:='${BRIDGE_CONFIG}'
    echo '--- ros_gz_bridge exited, restarting in 2s ---'
    sleep 2
  done
" > "${LOG_DIR}/ros_gz_bridge.log" 2>&1 &
disown

echo "Gazebo + ROS 2 bridge launched in the background (auto-restart on crash)."
echo "Logs: ${LOG_DIR}/gz_sim.log and ${LOG_DIR}/ros_gz_bridge.log"
