#!/usr/bin/env bash
# Starts robot_state_publisher, ros2_control_node (+ controllers) and move_group
# for the 3-joint 'arm' MoveIt 2 setup, in the background, then returns once
# move_group is ready to accept planning requests.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/bringup.log"
PID_FILE="$SCRIPT_DIR/bringup.pid"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

# Make this directory discoverable as the ament package "arm_moveit_config"
# (config/arm.urdf, config/arm.srdf, config/*.yaml) without needing a colcon build.
mkdir -p "$SCRIPT_DIR/ament_index/share/ament_index/resource_index/packages"
touch "$SCRIPT_DIR/ament_index/share/ament_index/resource_index/packages/arm_moveit_config"
ln -sfn "$SCRIPT_DIR" "$SCRIPT_DIR/ament_index/share/arm_moveit_config"
export AMENT_PREFIX_PATH="$SCRIPT_DIR/ament_index:${AMENT_PREFIX_PATH:-}"

# This host may run several unrelated ROS 2 graphs side by side (other sessions/
# containers sharing the same network namespace, all on the default DDS domain).
# Pin this stack to a domain ID derived from SCRIPT_DIR so it never talks to, or
# is confused with, an unrelated 'arm_controller'/'move_group' elsewhere on the
# host. plan.py reads the same file to compute the identical ID.
DOMAIN_ID_FILE="$SCRIPT_DIR/.ros_domain_id"
if [[ ! -f "$DOMAIN_ID_FILE" ]]; then
    python3 -c "
import hashlib
print(int(hashlib.sha256('$SCRIPT_DIR'.encode()).hexdigest(), 16) % 200 + 1)
" > "$DOMAIN_ID_FILE"
fi
export ROS_DOMAIN_ID
ROS_DOMAIN_ID="$(cat "$DOMAIN_ID_FILE")"
echo "Using ROS_DOMAIN_ID=$ROS_DOMAIN_ID (isolates this stack from other ROS graphs on the host)"

# If a previous bringup is still alive, don't start a second one.
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "bringup already running (PID $(cat "$PID_FILE"))"
else
    echo "Starting move_group stack in the background, logging to $LOG_FILE"
    nohup ros2 launch "$SCRIPT_DIR/bringup.launch.py" \
        > "$LOG_FILE" 2>&1 < /dev/null &
    LAUNCH_PID=$!
    disown "$LAUNCH_PID"
    echo "$LAUNCH_PID" > "$PID_FILE"
fi

echo "Waiting for /move_action action server to come up..."
TIMEOUT=120
ELAPSED=0
until ros2 action list 2>/dev/null | grep -q "^/move_action$"; do
    if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
        echo "ERROR: move_group did not become ready within ${TIMEOUT}s. See $LOG_FILE" >&2
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "move_group is up (waited ${ELAPSED}s)."

# Best-effort: give ros2_control's controllers a little time to become active too.
TIMEOUT=30
ELAPSED=0
until ros2 control list_controllers 2>/dev/null | grep -q "arm_controller.*active"; do
    if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
        echo "WARNING: arm_controller not confirmed active yet, continuing anyway." >&2
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "bringup complete."
exit 0
