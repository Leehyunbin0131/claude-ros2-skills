#!/usr/bin/env bash
# Starts move_group (and the robot_state_publisher / ros2_control stack it needs)
# in the background, then returns once the move_group action server is up.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/moveit_bringup.log"
DOMAIN_ID_FILE="$SCRIPT_DIR/.ros_domain_id"

source /opt/ros/jazzy/setup.bash

# The machine this runs on may host other, unrelated ROS 2 graphs. Pick a
# domain id derived from this directory's path so our nodes/services/actions
# (move_group, /apply_planning_scene, ...) never collide with someone else's,
# and persist it so plan.py can join the same domain.
export ROS_DOMAIN_ID=$(( $(cksum <<< "$SCRIPT_DIR" | cut -d' ' -f1) % 200 + 1 ))
echo "$ROS_DOMAIN_ID" > "$DOMAIN_ID_FILE"
echo "Using ROS_DOMAIN_ID=$ROS_DOMAIN_ID (see $DOMAIN_ID_FILE)"

setsid nohup ros2 launch "$SCRIPT_DIR/launch/bringup_launch.py" \
    > "$LOG_FILE" 2>&1 < /dev/null &
disown

echo "Launching MoveIt bringup in the background (log: $LOG_FILE)"

for i in $(seq 1 90); do
    if ros2 action list 2>/dev/null | grep -q "/move_action"; then
        echo "move_group is up and ready."
        exit 0
    fi
    sleep 1
done

echo "Timed out waiting for move_group to become ready. Check $LOG_FILE" >&2
exit 1
