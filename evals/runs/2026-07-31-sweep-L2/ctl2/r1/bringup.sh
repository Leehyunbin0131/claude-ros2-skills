#!/usr/bin/env bash
# Brings up ros2_control on mock_components/GenericSystem with joint_a/joint_b,
# then spawns joint_state_broadcaster and position_controller (active).
# Starts everything in the background and returns; no cleanup is performed.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

ROBOT_DESCRIPTION="$(cat "$DIR/robot.urdf")"

# Publishes /robot_description (and tf) for the two dummy links/joints.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  > "$DIR/robot_state_publisher.log" 2>&1 &
disown

# controller_manager gets the robot_description directly as a parameter.
nohup ros2 run controller_manager ros2_control_node \
  --ros-args \
  -p robot_description:="$ROBOT_DESCRIPTION" \
  --params-file "$DIR/controllers.yaml" \
  > "$DIR/controller_manager.log" 2>&1 &
disown

# Spawn + activate the controllers once controller_manager is reachable.
# Run this asynchronously too, so bringup.sh returns immediately.
(
  ros2 run controller_manager spawner \
    --controller-manager-timeout 60 \
    joint_state_broadcaster \
    > "$DIR/spawn_joint_state_broadcaster.log" 2>&1

  ros2 run controller_manager spawner \
    --controller-manager-timeout 60 \
    position_controller \
    > "$DIR/spawn_position_controller.log" 2>&1
) &
disown

exit 0
