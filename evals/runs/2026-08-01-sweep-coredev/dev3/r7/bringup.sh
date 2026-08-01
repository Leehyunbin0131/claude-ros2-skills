#!/usr/bin/env bash
# Starts the Nav2 navigation stack (controller_server + local/global costmaps,
# planner_server, bt_navigator, etc.) in the background against the map -> odom
# -> base_link -> laser_frame TF tree and /scan topic that are already being
# published, and returns immediately without waiting for shutdown.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_FILE="$SCRIPT_DIR/nav2_bringup.log"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch nav2_bringup navigation_launch.py \
    params_file:="$PARAMS_FILE" \
    use_sim_time:=false \
    autostart:=true \
    > "$LOG_FILE" 2>&1 &

disown

echo "Nav2 stack launching in background (launch PID $!). Logs: $LOG_FILE"
