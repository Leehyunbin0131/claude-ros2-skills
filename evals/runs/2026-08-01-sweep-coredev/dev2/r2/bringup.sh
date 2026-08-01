#!/usr/bin/env bash
# Starts the Nav2 controller_server, planner_server, behavior_server, bt_navigator
# and a lifecycle manager in the background, then returns immediately.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/nav2_logs"
mkdir -p "$LOG_DIR"

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

nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args --params-file "$PARAMS_FILE" \
  -r __node:=lifecycle_manager \
  > "$LOG_DIR/lifecycle_manager.log" 2>&1 &
disown

echo "Nav2 nodes launching in background. Logs in $LOG_DIR"
