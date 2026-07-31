#!/usr/bin/env bash
# Minimal ros2_control bringup: mock_components/GenericSystem hardware with
# joint_a and joint_b (position command; position+velocity state).
# Starts everything in the background and returns without waiting for shutdown.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "$DIR/bringup.launch.py" > "$DIR/bringup.log" 2>&1 &
disown

echo "Launching ros2_control bringup (log: $DIR/bringup.log)..."

# Wait for joint_state_broadcaster to report active before returning, so
# callers can immediately query /joint_states and list_controllers.
for i in $(seq 1 60); do
    if ros2 control list_controllers 2>/dev/null | grep -q "joint_state_broadcaster.*active"; then
        echo "joint_state_broadcaster is active."
        exit 0
    fi
    sleep 1
done

echo "Timed out waiting for joint_state_broadcaster to become active; check $DIR/bringup.log" >&2
exit 1
