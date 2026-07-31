#!/usr/bin/env bash
# Starts Gazebo (Harmonic), publishes /robot_description, spawns the robot
# into the running world, and bridges /clock + /imu to ROS 2. Everything
# runs in the background; this script returns as soon as it has kicked
# everything off. No cleanup is performed.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGDIR="$DIR/log"
mkdir -p "$LOGDIR"

source /opt/ros/jazzy/setup.bash

export GZ_SIM_RESOURCE_PATH="$DIR/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
WORLD_NAME="default"

# 1. Start the Gazebo world server in the background.
nohup gz sim -r -s -v 3 "$DIR/worlds/empty.world" > "$LOGDIR/gz_sim.log" 2>&1 &
disown

# 2. Publish /robot_description with use_sim_time so its clock (and TF)
#    track Gazebo time once the /clock bridge below comes up.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args \
  -p use_sim_time:=true \
  -p robot_description:="$(cat "$DIR/urdf/robot.urdf")" \
  > "$LOGDIR/robot_state_publisher.log" 2>&1 &
disown

# 3. Once the world is actually up, spawn the robot from /robot_description
#    and bridge /clock + /imu into ROS. Run this sequence in the
#    background too, so bringup.sh itself doesn't block on it.
(
  for i in $(seq 1 120); do
    if gz service -l 2>/dev/null | grep -q "/world/${WORLD_NAME}/create"; then
      break
    fi
    sleep 1
  done

  ros2 run ros_gz_sim create \
    -world "$WORLD_NAME" -topic /robot_description -name simple_bot -z 0.1 \
    > "$LOGDIR/spawn.log" 2>&1

  nohup ros2 run ros_gz_bridge parameter_bridge \
    /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
    /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
    --ros-args -p use_sim_time:=true \
    > "$LOGDIR/bridge.log" 2>&1 &
) > "$LOGDIR/sequence.log" 2>&1 &
disown

echo "bringup.sh: launched Gazebo, robot_state_publisher, spawn and bridge in the background."
echo "bringup.sh: logs in $LOGDIR"
