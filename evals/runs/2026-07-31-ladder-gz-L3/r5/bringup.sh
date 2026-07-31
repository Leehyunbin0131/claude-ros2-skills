#!/usr/bin/env bash
# Starts Gazebo, the ROS<->Gazebo bridge, robot_state_publisher and spawns
# the robot, all in the background. Returns immediately; nothing is cleaned
# up (kill the processes manually, e.g. `pkill -f imu_world` / `pkill -f
# ros_gz` / `pkill -f robot_state_publisher`, when done).

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$DIR/log"
mkdir -p "$LOG_DIR"

if [ -z "${ROS_DISTRO:-}" ]; then
  source /opt/ros/jazzy/setup.bash
fi
if [ -f /usr/share/gz/gz-sim8/setup.sh ]; then
  source /usr/share/gz/gz-sim8/setup.sh
fi

WORLD_NAME="imu_world"
ROBOT_NAME="my_robot"

echo "Logs: $LOG_DIR"

# 1. Start Gazebo (server only, running immediately) with our world.
nohup gz sim -s -r "$DIR/worlds/${WORLD_NAME}.sdf" > "$LOG_DIR/gz_sim.log" 2>&1 &
disown
echo "gz sim started (pid $!)"

# 2. Bridge /clock (sim time) and the raw IMU sensor topic to ROS 2.
nohup ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:="$DIR/config/bridge.yaml" -p use_sim_time:=true \
  > "$LOG_DIR/bridge.log" 2>&1 &
disown
echo "ros_gz_bridge started (pid $!)"

# 3. Publish /robot_description (and TF) via robot_state_publisher.
ROBOT_DESC="$(cat "$DIR/urdf/robot.urdf")"
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p use_sim_time:=true -p robot_description:="$ROBOT_DESC" \
  > "$LOG_DIR/rsp.log" 2>&1 &
disown
echo "robot_state_publisher started (pid $!)"

# 4. Once Gazebo's spawn service is up, spawn the robot from /robot_description.
(
  for _ in $(seq 1 60); do
    if gz service -l 2>/dev/null | grep -q "/world/${WORLD_NAME}/create"; then
      break
    fi
    sleep 1
  done
  ros2 run ros_gz_sim create -world "$WORLD_NAME" -topic /robot_description \
    -name "$ROBOT_NAME" -z 0.2
) > "$LOG_DIR/spawn.log" 2>&1 &
disown
echo "spawn watcher started (pid $!)"

# 5. Relay node: republish the bridged IMU data on /imu with
#    frame_id = imu_link (the URDF link the sensor is mounted on).
nohup python3 "$DIR/scripts/imu_frame_relay.py" --ros-args -p use_sim_time:=true \
  > "$LOG_DIR/imu_frame_relay.log" 2>&1 &
disown
echo "imu_frame_relay started (pid $!)"

echo "bringup.sh done; processes are running in the background."
