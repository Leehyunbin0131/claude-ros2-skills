#!/usr/bin/env bash
# Starts the core Nav2 servers + a lifecycle manager in the background and returns.
# Does not perform any cleanup / shutdown of the spawned processes.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

run_bg() {
  local name="$1"
  local pkg="$2"
  local exe="$3"
  setsid nohup ros2 run "$pkg" "$exe" --ros-args --params-file "$PARAMS_FILE" \
    > "$LOG_DIR/${name}.log" 2>&1 < /dev/null &
  disown
}

run_bg controller_server nav2_controller controller_server
run_bg planner_server nav2_planner planner_server
run_bg behavior_server nav2_behaviors behavior_server
run_bg bt_navigator nav2_bt_navigator bt_navigator

# lifecycle_manager stays alive to hold the bond with each managed node,
# and (with autostart:true) drives them through configure -> activate.
run_bg lifecycle_manager nav2_lifecycle_manager lifecycle_manager

echo "Nav2 servers launched in background (logs in $LOG_DIR). Waiting for activation..."

TIMEOUT=60
elapsed=0
while true; do
  c_state=$(ros2 lifecycle get /controller_server 2>/dev/null | awk '{print $1}')
  p_state=$(ros2 lifecycle get /planner_server 2>/dev/null | awk '{print $1}')
  if [ "$c_state" = "active" ] && [ "$p_state" = "active" ]; then
    echo "controller_server and planner_server are active."
    break
  fi
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "Timed out after ${TIMEOUT}s waiting for nodes to become active (controller_server=${c_state:-unknown}, planner_server=${p_state:-unknown})." >&2
    break
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done
