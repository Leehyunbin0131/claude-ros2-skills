#!/usr/bin/env bash
# Builds (if needed) and starts move_group plus its supporting nodes
# (robot_state_publisher, joint_state_publisher) in the background for the
# 3-joint 'arm' MoveIt planning group, then returns once move_group's
# move_action interface is ready.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/arm_ws"
LOG_FILE="/tmp/arm_moveit_bringup.log"

source /opt/ros/jazzy/setup.bash

if [ ! -f "${WS_DIR}/install/setup.bash" ]; then
    ( cd "${WS_DIR}" && colcon build --symlink-install )
fi

source "${WS_DIR}/install/setup.bash"

nohup ros2 launch arm_moveit_config move_group.launch.py > "${LOG_FILE}" 2>&1 &
disown

echo "move_group launching in background (pid $!), log: ${LOG_FILE}"

# Wait until the move_action action server is available before returning.
for i in $(seq 1 60); do
    if ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
        echo "move_group is ready."
        exit 0
    fi
    sleep 1
done

echo "WARNING: move_action action server not detected after 60s; check ${LOG_FILE}" >&2
exit 0
