#!/usr/bin/env bash
# Starts Gazebo (with the diff-drive robot + 360-sample GPU lidar world)
# and the ROS 2 <-> Gazebo bridge in the background, then returns.
# Logs go to ./log/*.log. Nothing is cleaned up on exit.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD="$DIR/world.sdf"
LOGDIR="$DIR/log"
mkdir -p "$LOGDIR"

source /opt/ros/jazzy/setup.bash

# This sandbox has no accessible /dev/dri render node, so Ogre2's
# headless-EGL GPU path can't init a context. The world is configured to
# use the legacy Ogre1 render engine for sensors, which works with Mesa's
# software rasterizer.
export LIBGL_ALWAYS_SOFTWARE=1

# --- Launch Gazebo Sim (server only, running, headless rendering) ---
nohup gz sim -s -r --headless-rendering "$WORLD" \
  > "$LOGDIR/gz_sim.log" 2>&1 < /dev/null &

# --- Wait (briefly) for the Gazebo transport layer to come up ---
for i in $(seq 1 60); do
  if gz topic -l 2>/dev/null | grep -q '^/clock$'; then
    break
  fi
  sleep 1
done

# --- Launch the ROS 2 <-> Gazebo Transport bridge ---
# /clock : Gz -> ROS   (rosgraph_msgs/msg/Clock)
# /cmd_vel : ROS -> Gz (geometry_msgs/msg/Twist)
# /scan  : Gz -> ROS   (sensor_msgs/msg/LaserScan, 360 samples)
nohup ros2 run ros_gz_bridge parameter_bridge \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist \
  /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan \
  --ros-args -p use_sim_time:=true \
  > "$LOGDIR/ros_gz_bridge.log" 2>&1 < /dev/null &

echo "bringup.sh: launched gz sim (pid $!) and ros_gz_bridge in the background."
echo "bringup.sh: logs in $LOGDIR"
