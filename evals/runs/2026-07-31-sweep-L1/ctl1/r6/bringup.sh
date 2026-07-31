#!/usr/bin/env bash
# Bring up a minimal ros2_control system (mock_components/GenericSystem)
# with two revolute joints (joint_a, joint_b) in the background.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

ROBOT_DESCRIPTION="$(cat "$DIR/urdf/robot.urdf")"

# Publish robot_description / TF.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  > "$LOG_DIR/robot_state_publisher.log" 2>&1 &
disown

# Start the controller manager with the mock hardware system.
nohup ros2 run controller_manager ros2_control_node \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  --params-file "$DIR/config/controllers.yaml" \
  > "$LOG_DIR/ros2_control_node.log" 2>&1 &
disown

# Wait for the controller manager to come up before spawning controllers.
for i in $(seq 1 30); do
  if ros2 control list_controllers >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

ros2 run controller_manager spawner joint_state_broadcaster \
  > "$LOG_DIR/spawner_joint_state_broadcaster.log" 2>&1 || true

ros2 run controller_manager spawner position_controller \
  > "$LOG_DIR/spawner_position_controller.log" 2>&1 || true
