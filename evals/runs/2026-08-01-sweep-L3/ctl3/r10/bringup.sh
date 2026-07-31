#!/usr/bin/env bash
# Starts the my_hw ros2_control stack in the background and returns.
# Does not clean up after itself.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ros2_ws"
LOG_FILE="/tmp/my_hw_bringup.log"

source /opt/ros/jazzy/setup.bash
source "$WS_DIR/install/setup.bash"

# Launch everything fully detached (own session) so it survives this
# script exiting, and log output for later inspection.
setsid nohup ros2 launch my_hw my_hw.launch.py > "$LOG_FILE" 2>&1 < /dev/null &
disown

echo "my_hw stack launching in background (log: $LOG_FILE)"

# Give the stack a bounded amount of time to come up before we hand
# control back, so callers don't have to guess how long to wait.
for i in $(seq 1 60); do
  if ros2 control list_hardware_components 2>/dev/null | grep -q "active" \
     && ros2 control list_controllers 2>/dev/null | grep -q "joint_state_broadcaster.*active"; then
    echo "my_hw stack is up."
    break
  fi
  sleep 1
done

exit 0
