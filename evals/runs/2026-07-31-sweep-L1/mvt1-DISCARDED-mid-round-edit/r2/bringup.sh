#!/usr/bin/env bash
# Builds (if needed) and launches move_group + everything it needs for the
# simple_arm MoveIt 2 setup in the background, then waits until move_group
# is actually up before returning. Does not clean up after itself.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source /opt/ros/jazzy/setup.bash

if [ ! -f install/setup.bash ]; then
    colcon build --symlink-install --packages-select simple_arm_moveit_config
fi

source install/setup.bash

mkdir -p log
nohup ros2 launch simple_arm_moveit_config move_group.launch.py \
    > "log/move_group_bringup.log" 2>&1 &
disown

echo "Launched move_group stack in background (PID $!), log at log/move_group_bringup.log"
echo "Waiting for /move_group node and /plan_kinematic_path service..."

TIMEOUT=120
START=$(date +%s)
while true; do
    if ros2 node list 2>/dev/null | grep -qx "/move_group" \
        && ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
        echo "move_group is up."
        break
    fi
    NOW=$(date +%s)
    if [ $((NOW - START)) -ge "$TIMEOUT" ]; then
        echo "Timed out after ${TIMEOUT}s waiting for move_group to come up." >&2
        echo "See log/move_group_bringup.log for details." >&2
        exit 1
    fi
    sleep 1
done
