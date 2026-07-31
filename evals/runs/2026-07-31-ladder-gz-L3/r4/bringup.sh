#!/usr/bin/env bash
# Brings up a Gazebo (gz sim) world, publishes /robot_description for the
# robot in robot.urdf, spawns it into the world, and bridges Gazebo's clock
# and the robot's IMU sensor into ROS 2. Starts everything in the background
# and returns; nothing here needs to be cleaned up by this script.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGDIR="$DIR/log"
mkdir -p "$LOGDIR"

source /opt/ros/jazzy/setup.bash

WORLD_NAME=bringup_world
ROBOT_NAME=imubot

(
  # Headless Gazebo server running our world.
  nohup gz sim -s -r "$DIR/world.sdf" > "$LOGDIR/gz_sim.log" 2>&1 &

  # Wait for the world's entity-spawning service to come up.
  for i in $(seq 1 60); do
    gz service -l 2>/dev/null | grep -q "/world/${WORLD_NAME}/create" && break
    sleep 1
  done

  # Publish /robot_description from robot.urdf (sim time, since it stamps TF).
  nohup ros2 run robot_state_publisher robot_state_publisher \
    --ros-args \
    -p use_sim_time:=true \
    -p "robot_description:=$(cat "$DIR/robot.urdf")" \
    > "$LOGDIR/robot_state_publisher.log" 2>&1 &

  sleep 2

  # Spawn the robot into the running world from the /robot_description topic.
  nohup ros2 run ros_gz_sim create \
    -topic /robot_description -name "$ROBOT_NAME" -world "$WORLD_NAME" -z 0.2 \
    > "$LOGDIR/spawn.log" 2>&1 &

  # Bridge Gazebo -> ROS 2: sim clock (so use_sim_time nodes see sim time)
  # and the robot's IMU (frame_id is forced to the mount link via the
  # <gz_frame_id> tag on the sensor in robot.urdf).
  nohup ros2 run ros_gz_bridge parameter_bridge \
    /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
    /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
    --ros-args -p use_sim_time:=true \
    > "$LOGDIR/bridge.log" 2>&1 &
) > "$LOGDIR/bringup_sequence.log" 2>&1 &

echo "Bringup launched in the background. Logs: $LOGDIR"
