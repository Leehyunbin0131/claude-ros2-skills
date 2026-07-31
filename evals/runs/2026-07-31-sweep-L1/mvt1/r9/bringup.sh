#!/usr/bin/env bash
# Starts move_group (and robot_state_publisher, ros2_control, controller
# spawners) for the 3-joint "arm3" MoveIt setup in the background, then
# returns. Does not stop/clean up the background processes.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

LOG_DIR="${SCRIPT_DIR}/log"
mkdir -p "$LOG_DIR"

setsid nohup ros2 launch "${SCRIPT_DIR}/launch/bringup.launch.py" \
    > "${LOG_DIR}/bringup.log" 2>&1 < /dev/null &
disown

echo "Launched MoveIt bringup in background (PID $!). Logs: ${LOG_DIR}/bringup.log"

# Wait (best-effort) until move_group and its planning service are up
# before returning, so callers can immediately query them.
for _ in $(seq 1 90); do
    if ros2 node list 2>/dev/null | grep -qx "/move_group" && \
       ros2 service list 2>/dev/null | grep -qx "/plan_kinematic_path"; then
        echo "move_group is up."
        exit 0
    fi
    sleep 1
done

echo "Warning: move_group did not report ready within timeout; check ${LOG_DIR}/bringup.log" >&2
exit 0
