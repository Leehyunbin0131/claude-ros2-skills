#!/usr/bin/env bash
# Starts Gazebo (Harmonic), spawns the robot described in robot.urdf into it,
# and bridges /clock and /imu to ROS 2. Everything is started in the
# background; this script does not wait for shutdown and does not clean up.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"

if [ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]; then
  # shellcheck disable=SC1091
  source "/opt/ros/${ROS_DISTRO}/setup.bash"
fi

mkdir -p "$DIR/log"

nohup ros2 launch "$DIR/bringup.launch.py" \
  > "$DIR/log/bringup.log" 2>&1 &
disown

echo "Bringup launched in the background (PID $!)."
echo "Logs: $DIR/log/bringup.log"
echo "Check with: ros2 topic echo /imu"
