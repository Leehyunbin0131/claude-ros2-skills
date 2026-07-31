#!/usr/bin/env bash
# Builds (if needed) and starts the MoveIt 2 demo (move_group + robot_state_publisher +
# ros2_control + controller spawners) for the 3-joint "arm" in the background, then
# waits until /move_group and /plan_kinematic_path are visible before returning.
# The launched processes are left running (no cleanup / trap on exit).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ws"

source /opt/ros/jazzy/setup.bash

if [ ! -f "$WS_DIR/install/setup.bash" ]; then
  (cd "$WS_DIR" && colcon build --symlink-install)
fi

source "$WS_DIR/install/setup.bash"

nohup ros2 launch arm_moveit_config demo.launch.py use_rviz:=false \
  > "$SCRIPT_DIR/move_group_bringup.log" 2>&1 &
disown

echo "Launched MoveIt bringup in background (PID $!). Log: $SCRIPT_DIR/move_group_bringup.log"

for i in $(seq 1 60); do
  if ros2 node list 2>/dev/null | grep -qx "/move_group" \
     && ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
    echo "move_group is up; /plan_kinematic_path is available."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for /move_group and /plan_kinematic_path" >&2
exit 1
