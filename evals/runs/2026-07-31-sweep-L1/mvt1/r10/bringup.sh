#!/usr/bin/env bash
# Starts move_group (and everything it needs) in the background for the
# arm_moveit_config MoveIt 2 setup, then returns.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ws"
LOG_FILE="$SCRIPT_DIR/move_group.log"

# ROS setup scripts reference variables that may be unset; keep -u off for them.
source /opt/ros/jazzy/setup.bash

if [ ! -f "$WS_DIR/install/setup.bash" ]; then
  (cd "$WS_DIR" && colcon build --symlink-install)
fi

source "$WS_DIR/install/setup.bash"

nohup ros2 launch arm_moveit_config bringup.launch.py > "$LOG_FILE" 2>&1 < /dev/null &
disown

echo "Launched arm_moveit_config bringup in the background (log: $LOG_FILE)."

# Wait for move_group to come up so callers can rely on it being ready
# as soon as this script returns. This does not stop the background
# processes if it times out.
for i in $(seq 1 60); do
  if ros2 node list 2>/dev/null | grep -qx "/move_group" \
     && ros2 service list 2>/dev/null | grep -q "/plan_kinematic_path"; then
    echo "move_group is up and /plan_kinematic_path is available."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for move_group to fully come up; check $LOG_FILE" >&2
exit 0
