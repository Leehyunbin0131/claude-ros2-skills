#!/bin/bash
# Starts the ros2_control system (mock GenericSystem, joint_state_broadcaster,
# and position_controller) in the background and returns once both
# controllers are active. Does not clean up after itself.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
fi
if [ -f "$SCRIPT_DIR/install/setup.bash" ]; then
  source "$SCRIPT_DIR/install/setup.bash"
fi

nohup ros2 launch "$SCRIPT_DIR/bringup_launch.py" > "$SCRIPT_DIR/bringup.log" 2>&1 &
disown

echo "Launched bringup in background (pid $!), waiting for controllers to activate..."

for i in $(seq 1 60); do
  status=$(ros2 control list_controllers 2>/dev/null)
  if echo "$status" | grep -q "joint_state_broadcaster.*active" && \
     echo "$status" | grep -q "position_controller.*active"; then
    echo "Both controllers are active."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for controllers to become active. Check $SCRIPT_DIR/bringup.log" >&2
exit 1
