#!/bin/bash
# Starts move_group (and everything it needs) for the simple 3-joint "arm"
# MoveIt 2 config, in the background. Returns once /move_group is up and
# the /plan_kinematic_path service is being served (or after a timeout).
# Does not clean up after itself.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/install/setup.bash"

LOG_FILE="${SCRIPT_DIR}/bringup.log"

nohup ros2 launch arm_moveit_config bringup.launch.py > "${LOG_FILE}" 2>&1 &
disown

echo "Launched arm_moveit_config bringup (PID $!), logging to ${LOG_FILE}"

# Wait for move_group to come up so the caller can rely on the node/service
# being present as soon as this script returns.
TIMEOUT=90
elapsed=0
while (( elapsed < TIMEOUT )); do
    if ros2 node list 2>/dev/null | grep -qx "/move_group" && \
       ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
        echo "move_group is up (after ${elapsed}s)."
        exit 0
    fi
    sleep 2
    elapsed=$(( elapsed + 2 ))
done

echo "Warning: move_group did not report ready within ${TIMEOUT}s; check ${LOG_FILE}" >&2
exit 0
