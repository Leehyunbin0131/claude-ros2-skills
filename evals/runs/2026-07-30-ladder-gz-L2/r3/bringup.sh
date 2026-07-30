#!/usr/bin/env bash
# Starts Gazebo Harmonic with the diff-drive + GPU lidar world, and the
# ros_gz_bridge topics needed to drive/read it from ROS 2. Everything is
# launched in the background; this script returns immediately and does not
# clean up after itself.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="$SCRIPT_DIR/world.sdf"

source /opt/ros/jazzy/setup.bash

# Gazebo simulation server (headless, real-time). Uses the on-screen X
# display for rendering since the GPU lidar sensor needs a working render
# context and headless-EGL is not available in this environment.
nohup gz sim -s -r "$WORLD_FILE" > /tmp/diffbot_gz.log 2>&1 &
disown

# Give the simulation a moment to come up before starting the bridge.
sleep 5

# ROS <-> Gazebo bridge: /cmd_vel (ROS -> GZ), /scan and /clock (GZ -> ROS).
nohup ros2 run ros_gz_bridge parameter_bridge \
  /cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
  /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  > /tmp/diffbot_bridge.log 2>&1 &
disown

echo "bringup started: gazebo pid group + ros_gz_bridge launched in background"
echo "  gazebo log:  /tmp/diffbot_gz.log"
echo "  bridge log:  /tmp/diffbot_bridge.log"
