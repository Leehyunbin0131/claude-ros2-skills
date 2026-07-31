#!/usr/bin/env bash
# Starts robot_state_publisher, ros2_control (with mock hardware), the
# joint_state_broadcaster / arm_controller spawners, and move_group for the
# simple 3-joint arm, all in the background. Returns once move_group's
# /move_action action server is available (or after a timeout).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HERE/logs"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

# Avoid stacking up multiple bringups.
if pgrep -f "bringup_launch.py" > /dev/null 2>&1; then
    echo "bringup already running, skipping re-launch"
else
    nohup ros2 launch "$HERE/bringup_launch.py" \
        > "$HERE/logs/bringup.log" 2>&1 &
    disown
fi

echo "Waiting for move_group action server (/move_action) to come up..."
for i in $(seq 1 90); do
    if ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
        echo "move_group is ready."
        exit 0
    fi
    sleep 1
done

echo "WARNING: timed out waiting for /move_action; check $HERE/logs/bringup.log" >&2
exit 0
