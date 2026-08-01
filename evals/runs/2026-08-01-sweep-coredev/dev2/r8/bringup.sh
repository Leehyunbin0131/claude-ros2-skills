#!/bin/bash
# Starts the core Nav2 stack (controller_server, planner_server, behavior_server,
# bt_navigator) plus a lifecycle_manager that autostarts them, all in the
# background. Waits until controller_server and planner_server report
# "active" before returning. Does not clean up after itself.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

if [ -z "${ROS_DISTRO:-}" ]; then
  source /opt/ros/jazzy/setup.bash
fi

# Nav2 needs a TF tree; publish a static map->odom->base_link chain since
# there is no localization/robot stack running here.
ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom \
  > "$LOG_DIR/tf_map_odom.log" 2>&1 &
disown

ros2 run tf2_ros static_transform_publisher --frame-id odom --child-frame-id base_link \
  > "$LOG_DIR/tf_odom_base_link.log" 2>&1 &
disown

ros2 run nav2_controller controller_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/controller_server.log" 2>&1 &
disown

ros2 run nav2_planner planner_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/planner_server.log" 2>&1 &
disown

ros2 run nav2_behaviors behavior_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/behavior_server.log" 2>&1 &
disown

ros2 run nav2_bt_navigator bt_navigator --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/bt_navigator.log" 2>&1 &
disown

ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/lifecycle_manager.log" 2>&1 &
disown

echo "Nav2 nodes launched (logs in $LOG_DIR). Waiting for activation..."

for i in $(seq 1 60); do
  ctrl_state=$(ros2 lifecycle get /controller_server 2>/dev/null | awk '{print $1}')
  plan_state=$(ros2 lifecycle get /planner_server 2>/dev/null | awk '{print $1}')
  if [ "$ctrl_state" = "active" ] && [ "$plan_state" = "active" ]; then
    echo "controller_server and planner_server are active."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for controller_server/planner_server to become active." >&2
exit 1
