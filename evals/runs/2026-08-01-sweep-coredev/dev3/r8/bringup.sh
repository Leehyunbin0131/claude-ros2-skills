#!/usr/bin/env bash
# Starts the Nav2 navigation stack (controller/planner/smoother/behavior servers,
# bt_navigator, waypoint_follower, velocity_smoother + a lifecycle manager) in the
# background and returns immediately. No cleanup is performed.
#
# Assumes /scan (sensor_msgs/msg/LaserScan, frame laser_frame) and the
# map -> odom -> base_link -> laser_frame transforms are already being published.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/nav2_logs"
mkdir -p "$LOG_DIR"

if [ -z "${ROS_DISTRO:-}" ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

start_node() {
  local pkg="$1" exe="$2" name="$3"
  shift 3
  nohup ros2 run "$pkg" "$exe" --ros-args \
      --params-file "$PARAMS_FILE" \
      -r __node:="$name" \
      "$@" \
      > "$LOG_DIR/${name}.log" 2>&1 &
  disown
}

# nav2_costmap_2d's default "costmap" topic is a nav_msgs/OccupancyGrid whose
# cost is compressed into the 0-100 occupancy range (and int8 can't exceed 127
# anyway), so a raw obstacle cost (e.g. 254) can never appear there. The
# uncompressed 0-255 cost lives on "costmap_raw" (nav2_msgs/msg/Costmap).
# Swap the two so that the raw cost data is what ends up on
# /local_costmap/costmap.
start_node nav2_controller         controller_server     controller_server \
    -r /local_costmap/costmap:=/local_costmap/costmap_occupancy \
    -r /local_costmap/costmap_raw:=/local_costmap/costmap
start_node nav2_smoother           smoother_server       smoother_server
start_node nav2_planner            planner_server        planner_server
start_node nav2_behaviors          behavior_server       behavior_server
start_node nav2_bt_navigator       bt_navigator          bt_navigator
start_node nav2_waypoint_follower  waypoint_follower     waypoint_follower
start_node nav2_velocity_smoother  velocity_smoother     velocity_smoother

nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
    -r __node:=lifecycle_manager_navigation \
    -p autostart:=true \
    -p node_names:="['controller_server','planner_server','smoother_server','behavior_server','bt_navigator','waypoint_follower','velocity_smoother']" \
    > "$LOG_DIR/lifecycle_manager_navigation.log" 2>&1 &
disown

echo "Nav2 stack launching in the background. Logs: $LOG_DIR"
