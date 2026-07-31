#!/usr/bin/env bash
# Starts move_group and everything it needs (robot_state_publisher, ros2_control,
# controller spawners) in the background and returns once move_group is ready.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

setsid nohup ros2 launch "$SCRIPT_DIR/launch/bringup_launch.py" \
    > "$LOG_DIR/bringup.log" 2>&1 < /dev/null &
LAUNCH_PID=$!
disown

echo "Launched MoveIt bringup in the background (pid $LAUNCH_PID)."
echo "Logs: $LOG_DIR/bringup.log"
echo "Waiting for move_group to become ready..."

for _ in $(seq 1 90); do
    if ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
        echo "move_group is ready."
        exit 0
    fi
    sleep 1
done

echo "Warning: timed out waiting for move_group to report ready; check $LOG_DIR/bringup.log" >&2
exit 0
