#!/usr/bin/env bash
# Starts Gazebo, spawns the robot described in robot.urdf, and bridges
# /clock and /imu into ROS 2. Everything ends up running in the background;
# this script returns once the robot has been spawned. Nothing is cleaned up.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_NAME="imu_world"
ROBOT_NAME="my_robot"
LOG_DIR="$DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

# 1. Start Gazebo (server only, running immediately) with a world that
#    loads the IMU sensor system plugin.
nohup gz sim -s -r -v 4 "$DIR/world.sdf" > "$LOG_DIR/gz_sim.log" 2>&1 &
disown

echo "Waiting for Gazebo world '$WORLD_NAME' to come up..."
for i in $(seq 1 60); do
  if gz service -l 2>/dev/null | grep -q "^/world/${WORLD_NAME}/create$"; then
    break
  fi
  sleep 1
done

# 2. Publish /robot_description (and TF) from the URDF, on simulation time.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p use_sim_time:=true -p "robot_description:=$(cat "$DIR/robot.urdf")" \
  > "$LOG_DIR/robot_state_publisher.log" 2>&1 &
disown

echo "Waiting for /robot_description to be published..."
for i in $(seq 1 60); do
  if ros2 topic list 2>/dev/null | grep -q "^/robot_description$"; then
    break
  fi
  sleep 1
done

# 3. Spawn the robot into the running Gazebo world from /robot_description.
#    This is a one-shot call, run synchronously.
ros2 run ros_gz_sim create \
  -world "$WORLD_NAME" -topic robot_description -name "$ROBOT_NAME" -z 0.2 \
  > "$LOG_DIR/spawn.log" 2>&1

# 4. Bridge the simulation clock and the IMU sensor data into ROS 2. The
#    raw IMU is bridged onto /imu/raw because Gazebo stamps its frame_id
#    with a scoped "model/link/sensor" path; see imu_frame_relay.py below.
nohup ros2 run ros_gz_bridge parameter_bridge \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
  --ros-args -p use_sim_time:=true -r /imu:=/imu/raw \
  > "$LOG_DIR/bridge.log" 2>&1 &
disown

# 5. Republish the IMU data on /imu with frame_id set to the URDF link
#    ("imu_link") the sensor is mounted on.
nohup python3 "$DIR/imu_frame_relay.py" \
  --ros-args -p use_sim_time:=true -p frame_id:=imu_link \
  > "$LOG_DIR/imu_frame_relay.log" 2>&1 &
disown

echo "Bringup complete. Logs in $LOG_DIR"
