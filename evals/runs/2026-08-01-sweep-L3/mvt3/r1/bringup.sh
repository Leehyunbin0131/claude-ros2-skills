#!/usr/bin/env bash
# Builds (if needed) and starts move_group + robot_state_publisher + joint_state_publisher
# for the simple_arm MoveIt 2 config, in the background, then returns once ready.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

colcon build --symlink-install --base-paths src

# shellcheck disable=SC1091
source install/setup.bash

mkdir -p log

# Stop any previous instance we started.
if [ -f log/move_group.pid ]; then
  old_pid="$(cat log/move_group.pid)"
  if kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 1
  fi
fi

nohup ros2 launch simple_arm_moveit_config demo.launch.py \
  > log/move_group.log 2>&1 &
launch_pid=$!
disown "$launch_pid"
echo "$launch_pid" > log/move_group.pid

echo "Started move_group launch (pid $launch_pid), waiting for it to become ready..."

ready=0
for _ in $(seq 1 90); do
  if ros2 service list 2>/dev/null | grep -q "^/get_planning_scene$" \
     && ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "Timed out waiting for move_group to start. See log/move_group.log" >&2
  exit 1
fi

echo "move_group is up (action /move_action, service /get_planning_scene)."
