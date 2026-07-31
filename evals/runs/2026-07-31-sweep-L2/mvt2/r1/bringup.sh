#!/usr/bin/env bash
# Builds (if needed) and starts move_group + robot_state_publisher + joint_state_publisher
# for the arm_moveit_config MoveIt 2 setup, in the background, then returns.
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set +u
source /opt/ros/jazzy/setup.bash

cd "$DIR"
if [ ! -d "$DIR/install/arm_moveit_config" ]; then
  colcon build --symlink-install --packages-select arm_moveit_config
fi

source "$DIR/install/setup.bash"
set -u

nohup ros2 launch arm_moveit_config move_group.launch.py \
  > "$DIR/move_group.log" 2>&1 &
disown

echo "move_group launch started in background (PID $!), logging to $DIR/move_group.log"
