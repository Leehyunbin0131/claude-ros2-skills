#!/usr/bin/env bash
# Brings up MoveIt 2 (move_group) for the arm3 3-joint revolute serial arm.
# Starts everything in the background and returns; nothing is cleaned up.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash
source "${SCRIPT_DIR}/install/setup.bash"

LOG_FILE="${SCRIPT_DIR}/move_group_bringup.log"

nohup ros2 launch arm3_moveit_config move_group.launch.py > "${LOG_FILE}" 2>&1 &
disown

echo "Launched arm3_moveit_config move_group stack (log: ${LOG_FILE})"

# Wait until move_group is fully up before returning, so callers can rely on
# `ros2 node list` / `ros2 service list` succeeding immediately afterwards.
for i in $(seq 1 60); do
    if ros2 node list 2>/dev/null | grep -qx "/move_group" \
        && ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
        echo "move_group is up (/move_group node, /plan_kinematic_path service)."
        exit 0
    fi
    sleep 1
done

echo "WARNING: timed out waiting for move_group to come up; check ${LOG_FILE}" >&2
exit 0
