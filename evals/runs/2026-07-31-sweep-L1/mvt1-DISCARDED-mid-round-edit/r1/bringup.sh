#!/usr/bin/env bash
# Builds (if needed) and starts the mini_arm MoveIt 2 setup (move_group + supporting
# nodes) in the background, then returns once /move_group is up and servicing
# /plan_kinematic_path. Does not stop or clean up the background processes.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source /opt/ros/jazzy/setup.bash

if [ ! -d "$SCRIPT_DIR/install" ]; then
  colcon build --symlink-install --packages-select mini_arm_moveit_config
fi

source "$SCRIPT_DIR/install/setup.bash"

LOG_FILE="$SCRIPT_DIR/bringup.log"
nohup ros2 launch mini_arm_moveit_config bringup.launch.py > "$LOG_FILE" 2>&1 < /dev/null &
disown

echo "Launching mini_arm MoveIt 2 setup in the background (log: $LOG_FILE)..."

for i in $(seq 1 120); do
  if ros2 node list 2>/dev/null | grep -qx "/move_group" \
      && ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
    echo "move_group is up and /plan_kinematic_path is available."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for /move_group to come up; check $LOG_FILE" >&2
exit 1
