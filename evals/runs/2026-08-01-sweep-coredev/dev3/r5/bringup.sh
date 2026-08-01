#!/usr/bin/env bash
# Starts the Nav2 navigation stack in the background and returns immediately.
# Assumes /scan (sensor_msgs/msg/LaserScan, frame laser_frame) and the
# map -> odom -> base_link -> laser_frame TF chain are already being published.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_FILE="${SCRIPT_DIR}/nav2_bringup_launch.py"
PARAMS_FILE="${SCRIPT_DIR}/nav2_params.yaml"
LOG_FILE="${SCRIPT_DIR}/nav2_bringup.log"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${LAUNCH_FILE}" \
    params_file:="${PARAMS_FILE}" \
    use_sim_time:=false \
    autostart:=true \
    > "${LOG_FILE}" 2>&1 &

disown

echo "Nav2 stack starting in background (PID $!). Logs: ${LOG_FILE}"
