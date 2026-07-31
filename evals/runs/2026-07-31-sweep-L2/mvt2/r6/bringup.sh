#!/usr/bin/env bash
# Starts move_group (and robot_state_publisher / joint_state_publisher) for the
# 3-joint 'arm3' robot in the background, then returns once the move_group
# action server is available.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/bringup.log"
PID_FILE="${SCRIPT_DIR}/bringup.pid"

source /opt/ros/jazzy/setup.bash

# If a previous bringup is already running, leave it alone.
if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
    echo "bringup already running (pid $(cat "${PID_FILE}"))"
    exit 0
fi

: > "${LOG_FILE}"

setsid nohup ros2 launch "${SCRIPT_DIR}/launch/bringup.launch.py" \
    >> "${LOG_FILE}" 2>&1 < /dev/null &
LAUNCH_PID=$!
echo "${LAUNCH_PID}" > "${PID_FILE}"
disown "${LAUNCH_PID}" 2>/dev/null || true

echo "launched bringup (pid ${LAUNCH_PID}), waiting for move_group action server..."

TIMEOUT_S=60
elapsed=0
until ros2 action list 2>/dev/null | grep -q "/move_action"; do
    if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
        echo "bringup process exited early, see ${LOG_FILE}" >&2
        exit 1
    fi
    if (( elapsed >= TIMEOUT_S )); then
        echo "timed out waiting for /move_action action server, see ${LOG_FILE}" >&2
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

echo "move_group is up (action /move_action available)."
exit 0
