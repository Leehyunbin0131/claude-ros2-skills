#!/usr/bin/env bash
# Starts robot_state_publisher, ros2_control, controllers and MoveIt move_group
# in the background, waits until move_group is ready to accept requests, then
# returns (the ROS 2 stack keeps running after this script exits).
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

source /opt/ros/jazzy/setup.bash

mkdir -p log

# Don't relaunch if already running.
if [ -f log/bringup.pid ] && kill -0 "$(cat log/bringup.pid)" 2>/dev/null; then
    echo "bringup already running (pid $(cat log/bringup.pid))"
else
    nohup ros2 launch "$HERE/launch/bringup.launch.py" > log/bringup.log 2>&1 &
    echo $! > log/bringup.pid
    disown
    echo "launched bringup (pid $(cat log/bringup.pid)), logging to log/bringup.log"
fi

# Wait for move_group's plan action server to be available.
echo "waiting for move_group action server..."
for i in $(seq 1 90); do
    if ros2 action list 2>/dev/null | grep -q "/move_action"; then
        echo "move_group is up."
        exit 0
    fi
    sleep 1
done

echo "WARNING: move_group did not come up within timeout; check log/bringup.log" >&2
exit 1
