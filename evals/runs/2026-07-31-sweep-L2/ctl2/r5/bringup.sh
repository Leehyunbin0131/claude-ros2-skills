#!/bin/bash
# Brings up a ros2_control system with mock_components/GenericSystem hosting
# two revolute joints (joint_a, joint_b), plus joint_state_broadcaster and
# a forward_command_controller/ForwardCommandController named
# position_controller commanding the position interface of both joints.
#
# Starts everything in the background and returns immediately. Does not
# clean up after itself.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/tmp/ros2_control_bringup"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

# This host may run other, unrelated ROS 2 sessions on the default domain
# (ROS_DOMAIN_ID=0), where DDS discovery would otherwise let our nodes latch
# onto a stray /robot_description (or other) topic from a different system.
# Pick a domain deterministically from this directory so re-runs stay
# consistent while staying isolated from everything else on the host.
export ROS_DOMAIN_ID=$(( $(cksum <<< "$SCRIPT_DIR" | cut -d' ' -f1) % 200 + 1 ))

URDF_CONTENT="$(cat "$SCRIPT_DIR/urdf/test_robot.urdf")"

# robot_state_publisher parses the URDF and publishes it on /robot_description
# (transient-local), which controller_manager subscribes to on startup.
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p robot_description:="$URDF_CONTENT" \
  > "$LOG_DIR/robot_state_publisher.log" 2>&1 &
disown

# controller_manager / ros2_control_node, loaded with the controller
# definitions from controllers.yaml.
ros2 run controller_manager ros2_control_node \
  --ros-args --params-file "$SCRIPT_DIR/config/controllers.yaml" \
  -p robot_description:="$URDF_CONTENT" \
  > "$LOG_DIR/controller_manager.log" 2>&1 &
disown

# Wait for controller_manager to come up, then load/activate the controllers.
# Runs in a backgrounded subshell so this script returns immediately.
(
  for i in $(seq 1 60); do
    if ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; then
      break
    fi
    sleep 1
  done

  ros2 run controller_manager spawner \
    joint_state_broadcaster \
    --controller-manager /controller_manager \
    > "$LOG_DIR/spawn_joint_state_broadcaster.log" 2>&1

  ros2 run controller_manager spawner \
    position_controller \
    --controller-manager /controller_manager \
    > "$LOG_DIR/spawn_position_controller.log" 2>&1
) > "$LOG_DIR/spawn_wrapper.log" 2>&1 &
disown

echo "ros2_control bringup started in the background."
echo "Logs: $LOG_DIR"
