#!/usr/bin/env bash
# Starts the Nav2 navigation stack in the background and returns immediately.
# Assumes:
#   - sensor_msgs/LaserScan is published on /scan in frame laser_frame
#   - map -> odom -> base_link -> laser_frame TF is published externally
# No map_server/amcl are started since map->odom is already provided.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/nav2_logs"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

run_node() {
  local pkg="$1" exe="$2" name="$3"
  shift 3
  nohup ros2 run "$pkg" "$exe" --ros-args --params-file "$PARAMS_FILE" "$@" \
    > "$LOG_DIR/${name}.log" 2>&1 &
  disown
}

# Controller server hosts the "local_costmap" sub-node. Remap costmap_raw
# (nav2_msgs/Costmap, raw 0-255 costs) onto the "costmap" topic name so that
# /local_costmap/costmap carries raw cost values (the default "costmap" topic
# is a nav_msgs/OccupancyGrid capped at 100 and can't reflect lethal cost).
run_node nav2_controller controller_server controller_server \
  -r /local_costmap/costmap:=/local_costmap/costmap_occupancygrid \
  -r /local_costmap/costmap_raw:=/local_costmap/costmap

# Planner server hosts the "global_costmap" sub-node.
run_node nav2_planner planner_server planner_server

run_node nav2_smoother smoother_server smoother_server
run_node nav2_behaviors behavior_server behavior_server
run_node nav2_bt_navigator bt_navigator bt_navigator
run_node nav2_waypoint_follower waypoint_follower waypoint_follower
run_node nav2_velocity_smoother velocity_smoother velocity_smoother

# Bring all managed nodes up to the active lifecycle state.
nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -p autostart:=true \
  -p node_names:="[controller_server, smoother_server, planner_server, behavior_server, bt_navigator, waypoint_follower, velocity_smoother]" \
  > "$LOG_DIR/lifecycle_manager.log" 2>&1 &
disown

echo "Nav2 stack launching in the background. Logs: $LOG_DIR"
