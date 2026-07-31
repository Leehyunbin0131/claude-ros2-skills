#!/usr/bin/env bash
# Brings up a ros2_control system (mock_components/GenericSystem) with two
# revolute joints (joint_a, joint_b), a joint_state_broadcaster and a
# forward_command_controller/ForwardCommandController named position_controller
# commanding the position interface of both joints.
#
# Starts the long-running nodes in the background (they keep running after
# this script exits) and only blocks long enough to spawn+activate the two
# controllers, so that by the time this script returns,
# `ros2 control list_controllers` reports both as active.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$ROS_DISTRO" ]; then
  source /opt/ros/jazzy/setup.bash
fi

URDF_FILE="$SCRIPT_DIR/robot.urdf"
CONTROLLERS_YAML="$SCRIPT_DIR/controllers.yaml"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

ROBOT_DESCRIPTION="$(cat "$URDF_FILE")"

echo "Starting robot_state_publisher..."
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" \
  > "$LOG_DIR/robot_state_publisher.log" 2>&1 &
disown

echo "Starting controller_manager (ros2_control_node)..."
nohup ros2 run controller_manager ros2_control_node \
  --ros-args -p robot_description:="$ROBOT_DESCRIPTION" --params-file "$CONTROLLERS_YAML" \
  > "$LOG_DIR/controller_manager.log" 2>&1 &
disown

echo "Waiting for controller_manager services to come up..."
until ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; do
  sleep 0.5
done
sleep 1

echo "Spawning joint_state_broadcaster..."
ros2 run controller_manager spawner joint_state_broadcaster \
  --controller-manager /controller_manager \
  > "$LOG_DIR/spawn_joint_state_broadcaster.log" 2>&1

echo "Spawning position_controller..."
ros2 run controller_manager spawner position_controller \
  --controller-manager /controller_manager \
  > "$LOG_DIR/spawn_position_controller.log" 2>&1

echo "Bringup complete. Logs in $LOG_DIR"
