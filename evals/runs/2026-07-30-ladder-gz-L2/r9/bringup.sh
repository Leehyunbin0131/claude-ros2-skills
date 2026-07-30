#!/usr/bin/env bash
# Launches Gazebo Harmonic with a diff-drive robot + GPU lidar, and the
# ros_gz_bridge topics needed to drive/read it from ROS 2 Jazzy.
# Everything is started in the background; this script returns immediately.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="$SCRIPT_DIR/diffbot_world.sdf"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

# Use simulation time for ROS nodes talking to Gazebo.
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"

# This sandbox has no /dev/dri GPU access, so --headless-rendering (which
# forces the EGL/device backend) fails. Instead we point Ogre2 at the
# existing X display, which lets it fall back to software GLX rendering
# (llvmpipe) -- needed for the GPU lidar sensor to actually render.
export DISPLAY="${DISPLAY:-:0}"

# --- Gazebo server (server-only, sim starts running immediately) -----
nohup gz sim -s -r "$WORLD_FILE" \
  > "$LOG_DIR/gz_sim.log" 2>&1 &
disown

# --- ros_gz_bridge: lidar scan, sim clock, cmd_vel --------------------
nohup ros2 run ros_gz_bridge parameter_bridge \
  /scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist \
  --ros-args -p use_sim_time:=true \
  > "$LOG_DIR/ros_gz_bridge.log" 2>&1 &
disown

echo "Gazebo + ros_gz_bridge launched in background."
echo "Logs: $LOG_DIR/gz_sim.log , $LOG_DIR/ros_gz_bridge.log"
