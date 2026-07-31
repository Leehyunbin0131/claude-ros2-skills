#!/usr/bin/env bash
# Starts move_group (plus robot_state_publisher and joint_state_publisher) for
# the 3-joint 'arm' MoveIt setup in the background, then returns once the
# move_group action server is ready.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${SCRIPT_DIR}/ws"
LOG_FILE="${SCRIPT_DIR}/moveit_bringup.log"

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

nohup ros2 launch arm_moveit_config move_group.launch.py \
    > "${LOG_FILE}" 2>&1 < /dev/null &
disown

echo "move_group launch started in background (pid $!), logging to ${LOG_FILE}"

for i in $(seq 1 60); do
    if ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
        echo "move_group is ready"
        exit 0
    fi
    sleep 1
done

echo "WARNING: move_group did not report ready within timeout; check ${LOG_FILE}" >&2
exit 0
