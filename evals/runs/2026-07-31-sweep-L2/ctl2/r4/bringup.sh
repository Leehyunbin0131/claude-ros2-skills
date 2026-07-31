#!/usr/bin/env bash
# Brings up ros2_control with a mock GenericSystem (joint_a, joint_b) plus
# joint_state_broadcaster and position_controller (ForwardCommandController).
# Launches everything in the background and returns; no cleanup is performed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

set -u

LOG_FILE="${SCRIPT_DIR}/bringup.log"

nohup ros2 launch "${SCRIPT_DIR}/bringup.launch.py" > "${LOG_FILE}" 2>&1 < /dev/null &
disown

echo "Launched ros2_control stack in background (log: ${LOG_FILE})"

# Wait until both controllers report 'active' so callers can rely on
# `ros2 control list_controllers` immediately after this script returns.
TIMEOUT=60
elapsed=0
while [ "${elapsed}" -lt "${TIMEOUT}" ]; do
    status=$(ros2 control list_controllers 2>/dev/null)
    if echo "${status}" | grep -q "joint_state_broadcaster.*active" && \
       echo "${status}" | grep -q "position_controller.*active"; then
        echo "Both controllers are active."
        exit 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

echo "Timed out waiting for controllers to become active; check ${LOG_FILE}" >&2
exit 0
