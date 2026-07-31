#!/usr/bin/env bash
# Starts robot_state_publisher, ros2_control, and MoveIt's move_group for the
# simple 3-joint arm in the background, then returns once move_group is ready.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/.bringup"
mkdir -p "${LOG_DIR}"

source /opt/ros/jazzy/setup.bash
set -u

# Kill any previous instance we started, so re-running bringup.sh is idempotent.
if [ -f "${LOG_DIR}/launch.pid" ]; then
  OLD_PID="$(cat "${LOG_DIR}/launch.pid" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
    kill -TERM -"${OLD_PID}" 2>/dev/null || kill "${OLD_PID}" 2>/dev/null
    sleep 2
  fi
fi

# Launch everything in its own process group, fully detached from this shell,
# so it keeps running after bringup.sh exits.
setsid nohup ros2 launch "${SCRIPT_DIR}/launch/bringup_launch.py" \
  > "${LOG_DIR}/bringup.log" 2>&1 < /dev/null &
LAUNCH_PID=$!
disown
echo "${LAUNCH_PID}" > "${LOG_DIR}/launch.pid"

echo "Started bringup (launch pid ${LAUNCH_PID}), logs at ${LOG_DIR}/bringup.log"
echo "Waiting for move_group to become ready..."

TIMEOUT=90
START_TIME=$(date +%s)
READY=0

while true; do
  NOW=$(date +%s)
  ELAPSED=$((NOW - START_TIME))
  if [ "${ELAPSED}" -ge "${TIMEOUT}" ]; then
    break
  fi

  if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    echo "ERROR: bringup process exited early, see ${LOG_DIR}/bringup.log" >&2
    exit 1
  fi

  ACTIONS="$(ros2 action list 2>/dev/null || true)"
  SERVICES="$(ros2 service list 2>/dev/null || true)"

  if echo "${ACTIONS}" | grep -q "/move_action" && \
     echo "${SERVICES}" | grep -q "/get_planning_scene" && \
     echo "${SERVICES}" | grep -q "/apply_planning_scene"; then
    READY=1
    break
  fi

  sleep 1
done

if [ "${READY}" -ne 1 ]; then
  echo "ERROR: move_group did not become ready within ${TIMEOUT}s, see ${LOG_DIR}/bringup.log" >&2
  exit 1
fi

echo "move_group is ready."
exit 0
