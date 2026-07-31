#!/bin/bash
# Brings up a ros2_control GenericSystem with two mock revolute joints
# (joint_a, joint_b) plus joint_state_broadcaster and position_controller.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

ROBOT_DESCRIPTION="$(cat "$SCRIPT_DIR/system.urdf")"

# robot_state_publisher: publishes /robot_description and TF
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p "robot_description:=${ROBOT_DESCRIPTION}" \
  > /tmp/robot_state_publisher.log 2>&1 &
disown

# controller_manager / ros2_control_node: loads the mock hardware + controllers
ros2 run controller_manager ros2_control_node \
  --ros-args \
  -p "robot_description:=${ROBOT_DESCRIPTION}" \
  --params-file "$SCRIPT_DIR/controllers.yaml" \
  > /tmp/ros2_control_node.log 2>&1 &
disown

# Wait for the controller_manager services to become available
until ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; do
  sleep 0.5
done
sleep 1

# Spawners block until the controller is loaded, configured and activated,
# then exit -- so it's safe to call them synchronously here.
ros2 run controller_manager spawner joint_state_broadcaster \
  --controller-manager /controller_manager

ros2 run controller_manager spawner position_controller \
  --controller-manager /controller_manager

echo "Bringup complete. Controllers:"
ros2 control list_controllers
