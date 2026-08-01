#!/usr/bin/env bash
#
# Starts the Nav2 navigation stack in the background and returns immediately.
#
# Assumes:
#   - sensor_msgs/msg/LaserScan is published on /scan in frame laser_frame
#   - the TF chain map -> odom -> base_link -> laser_frame is already
#     published by another process
#
# Nodes launched (all as ROS 2 lifecycle nodes, brought up by a
# lifecycle_manager with autostart:=true):
#   controller_server, smoother_server, planner_server, behavior_server,
#   bt_navigator, waypoint_follower, velocity_smoother
#
# The local costmap (owned by controller_server) marks obstacles from /scan
# and publishes on /local_costmap/costmap. By default Nav2 publishes an
# OccupancyGrid (0-100) on "costmap" and the raw uint8 cost values (0-255,
# with LETHAL_OBSTACLE=254) on "costmap_raw". This script remaps those two
# topics for the local costmap so that /local_costmap/costmap carries the
# raw nav2_msgs/msg/Costmap data instead.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="${SCRIPT_DIR}/nav2_params.yaml"
LOG_DIR="${SCRIPT_DIR}/nav2_logs"
mkdir -p "${LOG_DIR}"

if [ -z "${ROS_DISTRO:-}" ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

run_node() {
  local pkg="$1" exe="$2"
  shift 2
  setsid nohup ros2 run "${pkg}" "${exe}" --ros-args \
    --params-file "${PARAMS_FILE}" \
    -p use_sim_time:=false \
    "$@" \
    > "${LOG_DIR}/${exe}.log" 2>&1 < /dev/null &
  disown
}

# local_costmap is created inside controller_server; remap its raw (uint8,
# 0-255) costmap onto the standard "/local_costmap/costmap" topic name.
run_node nav2_controller controller_server \
  -r /local_costmap/costmap:=/local_costmap/costmap_occupancy_grid \
  -r /local_costmap/costmap_raw:=/local_costmap/costmap \
  -r cmd_vel:=cmd_vel_nav

run_node nav2_smoother smoother_server
run_node nav2_planner planner_server
run_node nav2_behaviors behavior_server -r cmd_vel:=cmd_vel_nav
run_node nav2_bt_navigator bt_navigator
run_node nav2_waypoint_follower waypoint_follower
run_node nav2_velocity_smoother velocity_smoother -r cmd_vel:=cmd_vel_nav

setsid nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -r __node:=lifecycle_manager_navigation \
  -p use_sim_time:=false \
  -p autostart:=true \
  -p node_names:="[controller_server,smoother_server,planner_server,behavior_server,velocity_smoother,bt_navigator,waypoint_follower]" \
  > "${LOG_DIR}/lifecycle_manager.log" 2>&1 < /dev/null &
disown

echo "Nav2 stack starting in the background. Logs: ${LOG_DIR}"
