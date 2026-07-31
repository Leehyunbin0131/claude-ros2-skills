#!/usr/bin/env bash
# Brings up: Gazebo (headless, running our world) -> robot_state_publisher
# (publishes /robot_description) -> spawns the robot from that topic via
# ros_gz_sim -> bridges /clock and /imu into ROS 2. Everything is launched
# in the background; this script does not wait for or clean up the
# processes it starts.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_NAME="default"
ROBOT_NAME="my_robot"

if [ -z "${ROS_DISTRO:-}" ]; then
  source /opt/ros/jazzy/setup.bash
fi

mkdir -p "$DIR/log"

# 1. Start Gazebo server (no GUI) running our world immediately.
nohup gz sim -s -r -v 4 "$DIR/world.sdf" > "$DIR/log/gz_sim.log" 2>&1 &
disown

# Wait for the world's UserCommands "create" service, so the spawn call
# below doesn't race against Gazebo startup.
for i in $(seq 1 30); do
  if ros2 service list 2>/dev/null | grep -q "/world/${WORLD_NAME}/create"; then
    break
  fi
  sleep 1
done

# 2. Publish the URDF on /robot_description (transient_local, so late
#    subscribers such as the spawner still receive it).
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args \
  -p "robot_description:=$(cat "$DIR/robot.urdf")" \
  -p use_sim_time:=true \
  > "$DIR/log/rsp.log" 2>&1 &
disown

sleep 2

# 3. Spawn the robot described on /robot_description into the running world.
nohup ros2 run ros_gz_sim create \
  -topic /robot_description \
  -name "$ROBOT_NAME" \
  -world "$WORLD_NAME" \
  -z 0.2 \
  > "$DIR/log/spawn.log" 2>&1 &
disown

# 4. Bridge simulation clock and the IMU sensor data into ROS 2.
nohup ros2 run ros_gz_bridge parameter_bridge \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /imu@sensor_msgs/msg/Imu[gz.msgs.IMU \
  --ros-args -p use_sim_time:=true \
  > "$DIR/log/bridge.log" 2>&1 &
disown

echo "Bringup launched (gz sim, robot_state_publisher, spawner, ros_gz_bridge)."
echo "Logs: $DIR/log/"
