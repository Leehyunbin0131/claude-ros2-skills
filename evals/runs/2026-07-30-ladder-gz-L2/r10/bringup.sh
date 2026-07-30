#!/usr/bin/env bash
# Starts Gazebo Harmonic with a diff-drive robot + 360-sample GPU lidar,
# and the ros_gz bridge for /cmd_vel, /scan, /clock. Runs everything in the
# background and returns immediately; nothing is cleaned up automatically.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="${SCRIPT_DIR}/world.sdf"
LOG_DIR="${SCRIPT_DIR}/.bringup_logs"
mkdir -p "${LOG_DIR}"

source /opt/ros/jazzy/setup.bash

# Launch Gazebo Harmonic server (no GUI). Do NOT pass --headless-rendering:
# in this environment the DRM render nodes (/dev/dri/*) are not accessible,
# but GLX rendering through the X display works and lets the GPU lidar sensor
# render correctly.
nohup gz sim -s -r -v 3 "${WORLD_FILE}" \
  > "${LOG_DIR}/gz_sim.log" 2>&1 &
disown

# Give the server a moment to come up before starting the bridge.
sleep 5

# Bridge:
#   /cmd_vel  ROS geometry_msgs/msg/Twist    -> GZ gz.msgs.Twist       (ROS -> GZ)
#   /scan     GZ  gz.msgs.LaserScan          -> ROS sensor_msgs/msg/LaserScan (GZ -> ROS)
#   /clock    GZ  gz.msgs.Clock              -> ROS rosgraph_msgs/msg/Clock   (GZ -> ROS)
nohup ros2 run ros_gz_bridge parameter_bridge \
  /cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
  /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  --ros-args -p use_sim_time:=true \
  > "${LOG_DIR}/ros_gz_bridge.log" 2>&1 &
disown

echo "bringup: gz sim + ros_gz_bridge started in background."
echo "bringup: logs in ${LOG_DIR}"
