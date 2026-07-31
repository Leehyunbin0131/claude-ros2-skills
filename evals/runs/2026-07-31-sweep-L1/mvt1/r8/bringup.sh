#!/usr/bin/env bash
# Builds (if needed) and starts move_group + everything it needs for the
# arm3r MoveIt 2 setup in the background, then returns.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ws"
LOG_FILE="/tmp/arm3r_move_group.log"

source /opt/ros/jazzy/setup.bash

if [ ! -f "$WS_DIR/install/setup.bash" ]; then
  ( cd "$WS_DIR" && colcon build --symlink-install )
fi

source "$WS_DIR/install/setup.bash"

nohup ros2 launch arm3r_moveit_config move_group.launch.py > "$LOG_FILE" 2>&1 &
disown

# Give move_group a chance to come up before returning, so callers can
# immediately rely on `ros2 node list` / `ros2 service list`.
for i in $(seq 1 60); do
  if ros2 node list 2>/dev/null | grep -qx "/move_group" && \
     ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
    echo "move_group is up (see $LOG_FILE for logs)."
    exit 0
  fi
  sleep 1
done

echo "Warning: move_group did not report ready within timeout; check $LOG_FILE" >&2
exit 0
