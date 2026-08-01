#!/usr/bin/env bash
# Brings up the Nav2 local costmap in the background and returns immediately.
#
# Assumes /scan (sensor_msgs/msg/LaserScan, frame laser_frame) and the
# map -> odom -> base_link -> laser_frame transforms are already published
# elsewhere.
#
# The standalone costmap node normally publishes two topics:
#   costmap      (nav_msgs/OccupancyGrid, values clamped to 0-100 for viz)
#   costmap_raw  (nav2_msgs/msg/Costmap, raw 0-255 cost values)
# Since we need /local_costmap/costmap to carry the raw 0-255 cost values
# (so lethal obstacle cells, cost 254, are visible above 250), the two are
# swapped via topic remaps below.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="${SCRIPT_DIR}/nav2_params.yaml"

source /opt/ros/jazzy/setup.bash

nohup ros2 run nav2_costmap_2d nav2_costmap_2d --ros-args \
  -r __node:=local_costmap -r __ns:=/local_costmap \
  --params-file "${PARAMS_FILE}" \
  -r costmap:=costmap_occupancy_grid -r costmap_raw:=costmap \
  > /tmp/local_costmap.log 2>&1 &
disown

nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -r __node:=lifecycle_manager_localcostmap -r __ns:=/local_costmap \
  -p node_names:="['local_costmap']" \
  -p autostart:=true \
  -p bond_timeout:=0.0 \
  -p use_sim_time:=false \
  > /tmp/local_costmap_lifecycle_manager.log 2>&1 &
disown

echo "Nav2 local costmap bringup launched in background (logs: /tmp/local_costmap.log, /tmp/local_costmap_lifecycle_manager.log)"
