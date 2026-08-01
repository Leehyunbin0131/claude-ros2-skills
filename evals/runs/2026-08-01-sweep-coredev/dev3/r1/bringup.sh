#!/usr/bin/env bash
# Starts the Nav2 navigation stack (controller_server w/ local_costmap,
# planner_server w/ global_costmap, behavior_server, bt_navigator,
# waypoint_follower, smoother_server, velocity_smoother + lifecycle_manager)
# in the background and returns immediately.
#
# Assumes /scan (sensor_msgs/msg/LaserScan, frame_id "laser_frame") and the
# map -> odom -> base_link -> laser_frame TF chain are already being
# published externally.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
# (ROS's setup.bash references unset variables, so this is sourced without `set -u`)
source /opt/ros/jazzy/setup.bash

nohup ros2 launch "${SCRIPT_DIR}/nav2_navigation_launch.py" \
    params_file:="${SCRIPT_DIR}/nav2_params.yaml" \
    use_sim_time:=false \
    autostart:=true \
    > "${SCRIPT_DIR}/nav2_bringup.log" 2>&1 &
disown

echo "Nav2 bringup started in background (PID $!). Logs: ${SCRIPT_DIR}/nav2_bringup.log"
