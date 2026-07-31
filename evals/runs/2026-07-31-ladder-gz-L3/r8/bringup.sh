#!/usr/bin/env bash
# Starts Gazebo (Harmonic), publishes /robot_description, spawns the robot
# into the running world, and bridges /clock and /imu to ROS 2. Everything
# is launched in the background; this script returns once things are up.
# No cleanup is performed - kill the processes manually when done.

set -o pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$DIR/log"
mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash

WORLD_NAME="default"

# 1. Start the Gazebo server, running immediately, with our world.
nohup gz sim -r -s "$DIR/world.sdf" > "$LOG_DIR/gz_sim.log" 2>&1 &
disown

# Wait for the world (and its "create" service) to be ready.
for _ in $(seq 1 60); do
    if gz service -l 2>/dev/null | grep -q "/world/${WORLD_NAME}/create"; then
        break
    fi
    sleep 1
done

# 2. Bridge the simulation clock so any node using use_sim_time gets
#    Gazebo time instead of wall time.
nohup ros2 run ros_gz_bridge parameter_bridge \
    /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
    --ros-args -p use_sim_time:=true \
    > "$LOG_DIR/bridge_clock.log" 2>&1 &
disown

# 3. Publish /robot_description from the URDF via robot_state_publisher.
ROBOT_DESC="$(cat "$DIR/robot.urdf")"
nohup ros2 run robot_state_publisher robot_state_publisher \
    --ros-args -p use_sim_time:=true -p "robot_description:=${ROBOT_DESC}" \
    > "$LOG_DIR/rsp.log" 2>&1 &
disown

# Wait for /robot_description to actually be published before spawning.
for _ in $(seq 1 30); do
    if ros2 topic list 2>/dev/null | grep -qx "/robot_description"; then
        break
    fi
    sleep 1
done

# 4. Spawn the robot into the running world, reading its description
#    straight from the /robot_description topic.
nohup ros2 run ros_gz_sim create \
    -world "$WORLD_NAME" -topic robot_description -name imu_bot -z 0.2 \
    > "$LOG_DIR/spawn.log" 2>&1 &
disown

# 5. Bridge the IMU sensor data out to ROS 2 on /imu.
nohup ros2 run ros_gz_bridge parameter_bridge \
    /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
    --ros-args -p use_sim_time:=true \
    > "$LOG_DIR/bridge_imu.log" 2>&1 &
disown

echo "Bringup launched (world=${WORLD_NAME}). Logs in ${LOG_DIR}"
