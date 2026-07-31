#!/usr/bin/env bash
# Starts move_group (plus robot_state_publisher and joint_state_publisher) for the
# three_dof_arm MoveIt 2 setup in the background, waits until it is ready to serve
# planning requests, then returns control to the caller. The launched processes
# keep running in the background after this script exits.
set -o pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$DIR/move_group.log"
PID_FILE="$DIR/move_group.pid"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

set -u

# If a previous instance is still running, stop its whole process group first
# (ros2 launch spawns move_group/robot_state_publisher/joint_state_publisher as
# children; killing only the launch PID would orphan them).
if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping previous move_group launch (pgid $OLD_PID)..."
        kill -TERM -- "-$OLD_PID" 2>/dev/null || true
        sleep 2
        kill -KILL -- "-$OLD_PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

echo "Launching move_group in the background (log: $LOG_FILE)..."
# setsid makes the launch process its own session/process-group leader, so its
# PID doubles as its PGID and the whole tree can be stopped together later.
setsid nohup ros2 launch "$DIR/launch/move_group.launch.py" > "$LOG_FILE" 2>&1 &
LAUNCH_PID=$!
disown "$LAUNCH_PID" 2>/dev/null || true
echo "$LAUNCH_PID" > "$PID_FILE"

echo "Waiting for move_group to become ready (pid $LAUNCH_PID)..."
READY=0
for i in $(seq 1 90); do
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
        echo "move_group launch process exited early. See $LOG_FILE" >&2
        exit 1
    fi

    if ros2 service list 2>/dev/null | grep -q "^/get_planning_scene$" \
        && ros2 service list 2>/dev/null | grep -q "^/apply_planning_scene$" \
        && ros2 action list 2>/dev/null | grep -q "^/move_action$"; then
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "Timed out waiting for move_group to become ready. See $LOG_FILE" >&2
    exit 1
fi

echo "move_group is up (pid $LAUNCH_PID)."
exit 0
