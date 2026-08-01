#!/usr/bin/env bash
# Launches the Nav2 controller_server, planner_server, behavior_server,
# bt_navigator and a lifecycle manager in the background, then returns.
# Nodes are left running (no cleanup / trap on exit).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="${SCRIPT_DIR}/nav2_params.yaml"
LOG_DIR="${SCRIPT_DIR}/log"
mkdir -p "${LOG_DIR}"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

start_node () {
  local pkg="$1" exe="$2" name="$3"
  nohup ros2 run "${pkg}" "${exe}" --ros-args --params-file "${PARAMS_FILE}" \
    > "${LOG_DIR}/${name}.log" 2>&1 &
  disown
  echo "started ${name} (pid $!)"
}

start_node nav2_controller controller_server controller_server
start_node nav2_planner planner_server planner_server
start_node nav2_behaviors behavior_server behavior_server
start_node nav2_bt_navigator bt_navigator bt_navigator

# Give the servers a moment to come up before the lifecycle manager
# tries to configure/activate them.
sleep 2

nohup ros2 run nav2_lifecycle_manager lifecycle_manager \
  --ros-args --params-file "${PARAMS_FILE}" -r __node:=lifecycle_manager_navigation \
  > "${LOG_DIR}/lifecycle_manager_navigation.log" 2>&1 &
disown
echo "started lifecycle_manager_navigation (pid $!)"

# Best-effort wait until the lifecycle manager has autostarted the nodes,
# without blocking indefinitely.
for i in $(seq 1 30); do
  state="$(ros2 lifecycle get /controller_server 2>/dev/null)"
  case "${state}" in
    active*) break ;;
  esac
  sleep 1
done

echo "Nav2 bringup launched. Logs in ${LOG_DIR}"
