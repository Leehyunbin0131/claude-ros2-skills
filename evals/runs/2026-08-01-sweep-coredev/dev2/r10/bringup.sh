#!/usr/bin/env bash
# Starts the core Nav2 stack (controller_server, planner_server, behavior_server,
# bt_navigator) plus a lifecycle manager that auto-configures/activates them.
# All nodes are launched detached in the background; this script returns once
# it has kicked them off. No cleanup / shutdown handling is provided.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="${SCRIPT_DIR}/nav2_params.yaml"
LOG_DIR="${SCRIPT_DIR}/log"

mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

run_node() {
  local pkg="$1" exe="$2" name="$3"
  nohup ros2 run "$pkg" "$exe" --ros-args --params-file "$PARAMS_FILE" \
    > "${LOG_DIR}/${name}.log" 2>&1 &
  disown
}

run_node nav2_controller       controller_server  controller_server
run_node nav2_planner          planner_server     planner_server
run_node nav2_behaviors        behavior_server    behavior_server
run_node nav2_bt_navigator     bt_navigator       bt_navigator
run_node nav2_lifecycle_manager lifecycle_manager lifecycle_manager

echo "Nav2 nodes launched in the background (logs in ${LOG_DIR})."

# Give the lifecycle manager time to configure/activate everything before
# handing control back, so the servers are already active by the time this
# script returns. The node processes themselves keep running in the
# background regardless of how long this wait takes.
wait_for_active() {
  local node="$1" timeout="${2:-60}" waited=0
  while [ "$waited" -lt "$timeout" ]; do
    if ros2 lifecycle get "$node" 2>/dev/null | grep -q "^active"; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

for n in /controller_server /planner_server /behavior_server /bt_navigator; do
  wait_for_active "$n" 60 || echo "Warning: $n did not become active within timeout" >&2
done
