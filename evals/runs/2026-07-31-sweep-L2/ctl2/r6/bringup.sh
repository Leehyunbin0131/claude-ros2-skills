#!/bin/bash
# Brings up a ros2_control mock GenericSystem with joint_a/joint_b, plus
# joint_state_broadcaster and a ForwardCommandController (position_controller).
# Starts the controller manager in the background and returns once both
# controllers are active. No cleanup is performed on exit.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source /opt/ros/jazzy/setup.bash

# Use a dedicated ROS domain so this bringup's /robot_description,
# /joint_states, etc. never collide with any other ROS graph already
# running on the host.
export ROS_DOMAIN_ID=77

mkdir -p "$DIR/log"

ROBOT_DESCRIPTION="$(ros2 run xacro xacro "$DIR/mock_robot.urdf.xacro")"

# robot_state_publisher publishes /robot_description (transient-local); the
# controller manager subscribes to that topic to obtain the URDF.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  > "$DIR/log/robot_state_publisher.log" 2>&1 < /dev/null &
disown

nohup ros2 run controller_manager ros2_control_node \
  --ros-args \
  -p robot_description:="$ROBOT_DESCRIPTION" \
  --params-file "$DIR/controllers.yaml" \
  > "$DIR/log/ros2_control_node.log" 2>&1 < /dev/null &
disown

# Wait until the controller manager's services are up.
for i in $(seq 1 60); do
  if ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; then
    break
  fi
  sleep 0.5
done

ros2 run controller_manager spawner joint_state_broadcaster \
  --controller-manager /controller_manager --controller-manager-timeout 30

ros2 run controller_manager spawner position_controller \
  --controller-manager /controller_manager --controller-manager-timeout 30
