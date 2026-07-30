#!/usr/bin/env bash
# Starts Gazebo Harmonic (gz sim) running the diff-drive + GPU-lidar world,
# and bridges /cmd_vel, /scan, /clock to ROS 2 Jazzy. Everything is launched
# fully detached in the background; this script returns immediately and does
# not wait on or clean up the spawned processes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_SDF="$SCRIPT_DIR/worlds/diff_drive_lidar.sdf"
LOG_DIR="$SCRIPT_DIR/log"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

# Gazebo's sensor renderer needs a display to initialize (even headless,
# server-only sim); default to :0 if the caller hasn't set one.
export DISPLAY="${DISPLAY:-:0}"

# Gazebo Sim server, running immediately, no GUI window.
setsid nohup gz sim -s -r -v 2 "$WORLD_SDF" \
  > "$LOG_DIR/gz_sim.log" 2>&1 < /dev/null &

# Give the world/sensors a few seconds to finish initializing before the
# bridge attaches, then start the ROS <-> Gazebo topic bridge. This waits
# in a detached background subshell so this script itself doesn't block.
(
  sleep 6
  exec ros2 run ros_gz_bridge parameter_bridge \
    /cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
    /scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan \
    /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
) > "$LOG_DIR/ros_gz_bridge.log" 2>&1 < /dev/null &

echo "Bringup started."
echo "  gz sim log:       $LOG_DIR/gz_sim.log"
echo "  ros_gz_bridge log: $LOG_DIR/ros_gz_bridge.log"
