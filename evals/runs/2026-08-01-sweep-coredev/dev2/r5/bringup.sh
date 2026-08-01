#!/usr/bin/env bash
#
# Starts the Nav2 controller_server, planner_server, behavior_server,
# bt_navigator, and a lifecycle_manager in the background, waits until
# controller_server and planner_server report "active", then returns.
# The launched nodes are left running in the background; no cleanup is
# performed by this script.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS="$DIR/nav2_params.yaml"
LOGDIR="$DIR/log"
mkdir -p "$LOGDIR"

# Make sure the ROS 2 environment is sourced.
if [ -z "$ROS_DISTRO" ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

echo "Starting Nav2 nodes (logs in $LOGDIR)..."

nohup ros2 run nav2_controller controller_server --ros-args --params-file "$PARAMS" \
  > "$LOGDIR/controller_server.log" 2>&1 &

nohup ros2 run nav2_planner planner_server --ros-args --params-file "$PARAMS" \
  > "$LOGDIR/planner_server.log" 2>&1 &

nohup ros2 run nav2_behaviors behavior_server --ros-args --params-file "$PARAMS" \
  > "$LOGDIR/behavior_server.log" 2>&1 &

nohup ros2 run nav2_bt_navigator bt_navigator --ros-args --params-file "$PARAMS" \
  > "$LOGDIR/bt_navigator.log" 2>&1 &

nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args --params-file "$PARAMS" \
  > "$LOGDIR/lifecycle_manager.log" 2>&1 &

disown -a 2>/dev/null

echo "Waiting for controller_server and planner_server to become active..."
for i in $(seq 1 90); do
  cs_state="$(ros2 lifecycle get /controller_server 2>/dev/null | awk '{print $1}')"
  ps_state="$(ros2 lifecycle get /planner_server 2>/dev/null | awk '{print $1}')"
  if [ "$cs_state" = "active" ] && [ "$ps_state" = "active" ]; then
    echo "controller_server and planner_server are active."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for controller_server/planner_server to become active." >&2
echo "Check logs in $LOGDIR for details." >&2
exit 1
