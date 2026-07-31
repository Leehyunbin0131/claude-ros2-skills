#!/usr/bin/env bash
# Starts Gazebo, spawns the robot described by robot.urdf into it, bridges
# /clock and /imu into ROS 2, and returns. Everything runs in the background;
# nothing here is cleaned up automatically.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$ROS_DISTRO" ]; then
  source /opt/ros/jazzy/setup.bash
fi

mkdir -p "$DIR/log"

# 1. Start Gazebo (server only, headless, running immediately) with our world.
GZ_SIM_RESOURCE_PATH="$DIR${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}" \
  nohup gz sim -s -r -v 3 "$DIR/world.sdf" \
  > "$DIR/log/gz_sim.log" 2>&1 &
disown

# Give the Gazebo server time to come up and advertise its services/topics.
sleep 5

# 2. Publish the URDF on /robot_description (and TF), synced to sim time.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args \
  -p use_sim_time:=true \
  -p robot_description:="$(cat "$DIR/robot.urdf")" \
  > "$DIR/log/robot_state_publisher.log" 2>&1 &
disown

sleep 2

# 3. Spawn the robot into the already-running Gazebo world from /robot_description.
nohup ros2 run ros_gz_sim create \
  -topic /robot_description \
  -name my_robot \
  -z 0.2 \
  > "$DIR/log/spawn.log" 2>&1 &
disown

# 4. Bridge Gazebo's simulation clock and the IMU sensor data into ROS 2.
nohup ros2 run ros_gz_bridge parameter_bridge \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
  --ros-args -p use_sim_time:=true \
  > "$DIR/log/bridge.log" 2>&1 &
disown

echo "Bringup started. Logs in $DIR/log/"
echo "Check with: ros2 topic echo /imu"
