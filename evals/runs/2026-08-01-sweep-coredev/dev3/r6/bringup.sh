#!/usr/bin/env bash
# Starts the Nav2 navigation stack in the background and returns immediately.
# Assumes ROS 2 Jazzy + Nav2 are installed, /scan is being published in
# frame laser_frame, and map->odom->base_link->laser_frame TF is already
# being published by another process.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ROS 2's setup.bash references unset variables internally, so 'set -u'
# would break sourcing it; keep nounset off for this whole script.
source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/nav2_navigation_launch.py" \
    params_file:="${SCRIPT_DIR}/nav2_params.yaml" \
    use_sim_time:=false \
    autostart:=true \
    > "${SCRIPT_DIR}/nav2_bringup.log" 2>&1 &

disown

echo "Nav2 bringup launched in background (PID $!). Logs: ${SCRIPT_DIR}/nav2_bringup.log"
