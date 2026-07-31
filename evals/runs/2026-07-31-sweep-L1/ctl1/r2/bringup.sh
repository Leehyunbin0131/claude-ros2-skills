#!/usr/bin/env bash
# Minimal ros2_control bringup using mock_components/GenericSystem.
# Starts robot_state_publisher + controller_manager in the background,
# spawns joint_state_broadcaster, then returns. No cleanup performed.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URDF_FILE="$SCRIPT_DIR/robot.urdf"
CONTROLLERS_YAML="$SCRIPT_DIR/controllers.yaml"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

ROBOT_DESCRIPTION="$(cat "$URDF_FILE")"

# robot_state_publisher publishes /robot_description, which controller_manager
# subscribes to in order to parse the <ros2_control> hardware description.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  > "$LOG_DIR/robot_state_publisher.log" 2>&1 &
disown

nohup ros2 run controller_manager ros2_control_node \
  --ros-args --params-file "$CONTROLLERS_YAML" \
  > "$LOG_DIR/controller_manager.log" 2>&1 &
disown

# Wait for the controller_manager services to come up before spawning.
for i in $(seq 1 60); do
  if ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; then
    break
  fi
  sleep 1
done

ros2 run controller_manager spawner joint_state_broadcaster \
  --controller-manager /controller_manager \
  > "$LOG_DIR/spawner_joint_state_broadcaster.log" 2>&1

echo "Bringup complete. Logs in $LOG_DIR"
