#!/usr/bin/env bash
# Starts the Nav2 controller_server, planner_server, behavior_server, bt_navigator
# and a lifecycle_manager in the background, then returns once controller_server
# and planner_server report 'active' (or a timeout elapses). Does not clean up
# after itself; the nodes keep running once this script exits.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

nohup ros2 run nav2_controller controller_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/controller_server.log" 2>&1 &
disown
nohup ros2 run nav2_planner planner_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/planner_server.log" 2>&1 &
disown
nohup ros2 run nav2_behaviors behavior_server --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/behavior_server.log" 2>&1 &
disown
nohup ros2 run nav2_bt_navigator bt_navigator --ros-args --params-file "$PARAMS_FILE" \
  > "$LOG_DIR/bt_navigator.log" 2>&1 &
disown

# Give the servers a moment to come up before the lifecycle manager looks for them.
sleep 3

nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -p autostart:=true \
  -p "node_names:=['controller_server','planner_server','behavior_server','bt_navigator']" \
  -r __node:=lifecycle_manager_navigation \
  > "$LOG_DIR/lifecycle_manager.log" 2>&1 &
disown

# Wait (bounded) for the two required nodes to reach 'active' before returning.
for i in $(seq 1 30); do
  c_state=$(ros2 lifecycle get /controller_server 2>/dev/null)
  p_state=$(ros2 lifecycle get /planner_server 2>/dev/null)
  if [[ "$c_state" == active* && "$p_state" == active* ]]; then
    echo "controller_server and planner_server are active."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for controller_server/planner_server to become active; check $LOG_DIR/*.log" >&2
exit 1
