#!/usr/bin/env bash
# Brings up the my_hw ros2_control stack (controller_manager + custom hardware
# component + joint_state_broadcaster + forward_position_controller) in the
# background and returns. Does not clean up after itself.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash
source "$SCRIPT_DIR/install/setup.bash"

LOG_DIR="$SCRIPT_DIR/bringup_logs"
mkdir -p "$LOG_DIR"

nohup ros2 launch my_hw my_hw.launch.py > "$LOG_DIR/launch.log" 2>&1 < /dev/null &
disown

# Briefly poll (bounded, non-blocking beyond ~30s) so that commands run right
# after this script returns already see everything active. The launched
# stack keeps running in the background regardless of whether this loop
# times out.
for _ in $(seq 1 60); do
    if ros2 control list_hardware_components 2>/dev/null | grep -q "label=active" \
        && ros2 control list_controllers 2>/dev/null | grep -q "^joint_state_broadcaster .*active" \
        && timeout 2 ros2 topic echo /joint_states --once --field name 2>/dev/null | grep -q "joint_a"; then
        break
    fi
    sleep 0.5
done

exit 0
