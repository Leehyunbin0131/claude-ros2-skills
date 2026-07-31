#!/usr/bin/env bash
# Brings up robot_state_publisher, joint_state_publisher and move_group for
# the 3-joint "arm" planning group, in the background, then returns once
# move_group is ready to accept planning requests.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${ROS_DISTRO:-}" ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

LOG_DIR="${SCRIPT_DIR}/.bringup_logs"
mkdir -p "${LOG_DIR}"

nohup ros2 launch "${SCRIPT_DIR}/bringup.launch.py" \
  > "${LOG_DIR}/bringup.log" 2>&1 < /dev/null &
disown

echo "Launched move_group stack (PID $!), logs in ${LOG_DIR}/bringup.log"

echo "Waiting for move_group action server to become available..."
READY=0
for i in $(seq 1 60); do
  if ros2 action list 2>/dev/null | grep -q "/move_action"; then
    READY=1
    break
  fi
  sleep 1
done

if [ "${READY}" -eq 1 ]; then
  echo "move_group is up."
else
  echo "WARNING: move_group did not report ready within timeout; check ${LOG_DIR}/bringup.log" >&2
fi

exit 0
