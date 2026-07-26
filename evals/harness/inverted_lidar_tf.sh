#!/usr/bin/env bash
# Publish the Task 2 TF tree: map -> odom -> base_link -> rear_lidar, where the
# LiDAR transform declares roll 180 deg (upside-down) and yaw 180 deg (backward).
#
# This is the state `check_tf_tree.py --sensors rear_lidar` must flag. The
# map->odom and odom->base_link links are identity, present only so the global
# chain resolves the way it does on a real robot.
#
# Arg format verified against the install:
#   ros2 run tf2_ros static_transform_publisher --help
# -> named args, RPY in RADIANS.
set -euo pipefail

PI=3.14159265358979

trap 'kill 0' EXIT INT TERM

ros2 run tf2_ros static_transform_publisher \
  --frame-id map --child-frame-id odom &

ros2 run tf2_ros static_transform_publisher \
  --frame-id odom --child-frame-id base_link &

ros2 run tf2_ros static_transform_publisher \
  --frame-id base_link --child-frame-id rear_lidar \
  --x -0.10 --y 0.0 --z 0.15 \
  --roll "$PI" --pitch 0.0 --yaw "$PI" &

echo "map -> odom -> base_link -> rear_lidar published (rear_lidar: roll 180, yaw 180)."
echo "Ctrl-C to stop."
wait
