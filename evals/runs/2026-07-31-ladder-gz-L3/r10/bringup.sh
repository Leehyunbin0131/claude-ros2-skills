#!/usr/bin/env bash
# Brings up: Gazebo (headless server) + robot_state_publisher (/robot_description)
# + ros_gz_sim spawn of robot.urdf into the running world + ros_gz_bridge for
# /clock and /imu. Everything is started in the background; this script does
# not wait for or clean up the processes it starts.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

mkdir -p "$DIR/log"

# 1. Gazebo server, headless, running our world (has the Imu system plugin
#    loaded so any IMU sensor on a spawned model is serviced).
nohup gz sim -s -r -v3 "$DIR/world.sdf" \
  > "$DIR/log/gz_sim.log" 2>&1 &

# 2. robot_state_publisher: reads robot.urdf, publishes /robot_description
#    and /tf, using sim time.
nohup ros2 run robot_state_publisher robot_state_publisher \
  --ros-args \
  -p use_sim_time:=true \
  -p "robot_description:=$(cat "$DIR/robot.urdf")" \
  > "$DIR/log/robot_state_publisher.log" 2>&1 &

# 3. Bridge Gazebo -> ROS 2 for sim clock and the IMU sensor reading
#    (see bridge.yaml for why the IMU is bridged to an internal topic).
nohup ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:="$DIR/bridge.yaml" -p use_sim_time:=true \
  > "$DIR/log/ros_gz_bridge.log" 2>&1 &

# 3b. Fix up the IMU's frame_id to the mounting link's name and republish
#     on /imu.
nohup python3 "$DIR/imu_frame_fix.py" \
  --ros-args -p use_sim_time:=true -p frame_id:=imu_link \
  > "$DIR/log/imu_frame_fix.log" 2>&1 &

# 4. Spawn the robot (read from the /robot_description topic) into the
#    running world. This call waits for Gazebo's create service on its own,
#    so no extra sleep is required.
nohup ros2 run ros_gz_sim create \
  -world default \
  -topic /robot_description \
  -name simple_robot \
  -z 0.5 \
  > "$DIR/log/spawn.log" 2>&1 &

echo "bringup started. Logs in $DIR/log/"
exit 0
