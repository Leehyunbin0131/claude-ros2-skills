#!/usr/bin/env bash
# Launches the my_hw ros2_control demo (custom SystemInterface hardware plugin
# for joint_a/joint_b) in the background and returns. Does not clean up after
# itself; kill the launched processes manually when done.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ws"
LOG_FILE="/tmp/my_hw_bringup.log"

source /opt/ros/jazzy/setup.bash
source "$WS_DIR/install/setup.bash"

nohup ros2 launch my_hw bringup.launch.py > "$LOG_FILE" 2>&1 &
disown

echo "my_hw bringup launched in background (log: $LOG_FILE)"

# Best-effort wait until the controller manager and controllers are up, so
# that commands issued right after this script returns will find everything
# ready. This does not block indefinitely: it gives up after ~60s either way.
for _ in $(seq 1 60); do
  if ros2 control list_controllers 2>/dev/null | grep -q "joint_state_broadcaster.*active" \
    && ros2 control list_controllers 2>/dev/null | grep -q "forward_position_controller.*active"; then
    echo "Controllers are active."
    break
  fi
  sleep 1
done
