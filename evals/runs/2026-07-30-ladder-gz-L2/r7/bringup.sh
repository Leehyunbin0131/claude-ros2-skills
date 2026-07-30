#!/usr/bin/env bash
# Starts Gazebo Harmonic (with the diff-drive + GPU-lidar world) and the
# ros_gz_bridge in the background, then returns immediately.
#
# After `bash bringup.sh`, from ROS 2 you can:
#   ros2 topic echo /scan     -> sensor_msgs/msg/LaserScan, 360 finite ranges
#   ros2 topic echo /clock    -> rosgraph_msgs/msg/Clock
#   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
#     "{linear: {x: 0.5}, angular: {z: 0.2}}" -1   -> drives the robot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="$SCRIPT_DIR/diff_drive_lidar.sdf"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

# Gazebo's Sensors system needs a display to initialize its render context
# for the GPU lidar in this environment; direct headless EGL device access
# (/dev/dri) is not permitted here, but rendering via the X11 display works.
export DISPLAY="${DISPLAY:-:0}"
export GZ_SIM_RESOURCE_PATH="$SCRIPT_DIR${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"

# Start the Gazebo Harmonic server (physics, GPU lidar sensor, diff drive),
# fully detached so it keeps running after this script exits.
setsid nohup gz sim -s -r "$WORLD_FILE" \
  > "$LOG_DIR/gz_sim.log" 2>&1 < /dev/null &
disown

sleep 5

# Bridge sim <-> ROS 2:
#   /clock   gz -> ROS  (rosgraph_msgs/msg/Clock)
#   /scan    gz -> ROS  (sensor_msgs/msg/LaserScan, 360 samples)
#   /cmd_vel ROS -> gz  (geometry_msgs/msg/Twist)
setsid nohup ros2 run ros_gz_bridge parameter_bridge \
  /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock \
  /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan \
  /cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
  --ros-args -r __node:=ros_gz_bridge_node \
  > "$LOG_DIR/ros_gz_bridge.log" 2>&1 < /dev/null &
disown

echo "Gazebo Harmonic + ros_gz_bridge launched in the background."
echo "  gz sim log:        $LOG_DIR/gz_sim.log"
echo "  ros_gz_bridge log: $LOG_DIR/ros_gz_bridge.log"
echo "ROS 2 topics: /clock, /scan, /cmd_vel"
