#!/usr/bin/env bash
# Starts the Nav2 local costmap stack in the background and returns.
# Assumes /scan (sensor_msgs/LaserScan, frame laser_frame) is already being
# published, and that map -> odom -> base_link -> laser_frame TF is already
# being published by another process.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"

source /opt/ros/jazzy/setup.bash

# Local costmap lifecycle node. Namespace + name combine to the well-known
# fully-qualified node name /local_costmap/local_costmap.
#
# By default Nav2 publishes two forms of the costmap: an OccupancyGrid on
# "costmap" scaled down to the 0..100 range, and the raw uint8 (0..255) cost
# values as nav2_msgs/msg/Costmap on "costmap_raw". A lethal obstacle cell
# has raw cost 254, which the 0..100 grid can never represent, so the raw
# topic is remapped onto the "costmap" name to expose real 0..255 costs on
# /local_costmap/costmap.
nohup ros2 run nav2_costmap_2d nav2_costmap_2d --ros-args \
  -r __name:=local_costmap \
  -r __ns:=/local_costmap \
  -r costmap:=costmap_occupancy_grid \
  -r costmap_raw:=costmap \
  --params-file "$PARAMS_FILE" \
  > "$SCRIPT_DIR/local_costmap.log" 2>&1 &
disown

# Lifecycle manager to auto configure+activate the costmap node.
# bond_timeout is disabled because the standalone costmap node does not
# create a bond connection back to the lifecycle manager.
nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -r __node:=lifecycle_manager_costmap \
  -p autostart:=true \
  -p bond_timeout:=0.0 \
  -p node_names:="['/local_costmap/local_costmap']" \
  -p use_sim_time:=false \
  > "$SCRIPT_DIR/lifecycle_manager.log" 2>&1 &
disown

echo "Nav2 local costmap stack launched in background (logs: $SCRIPT_DIR/local_costmap.log, $SCRIPT_DIR/lifecycle_manager.log)"
