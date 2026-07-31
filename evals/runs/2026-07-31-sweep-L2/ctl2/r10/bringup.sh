#!/usr/bin/env bash
# Brings up ros2_control (mock_components/GenericSystem, joints joint_a/joint_b)
# with joint_state_broadcaster and position_controller (ForwardCommandController).
# Long-running nodes are started in the background; the script returns once
# the controllers have been loaded, configured and activated.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

mkdir -p "$DIR/log"

ROBOT_DESC="$(cat "$DIR/robot.urdf")"

nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESC" -p use_sim_time:=false \
  > "$DIR/log/robot_state_publisher.log" 2>&1 &
disown

nohup ros2 run controller_manager ros2_control_node \
  --ros-args --params-file "$DIR/controllers.yaml" \
  > "$DIR/log/ros2_control_node.log" 2>&1 &
disown

# spawner waits for the controller_manager services to come up, then loads,
# configures and activates both controllers before exiting. Retry a couple of
# times in case controller loading races with the node still starting up.
for i in 1 2 3 4 5; do
  ros2 run controller_manager spawner \
    joint_state_broadcaster position_controller \
    -c controller_manager --controller-manager-timeout 30 \
    >> "$DIR/log/spawner.log" 2>&1 && break
  sleep 1
done
