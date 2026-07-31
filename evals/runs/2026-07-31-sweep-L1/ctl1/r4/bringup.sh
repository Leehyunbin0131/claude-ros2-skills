#!/usr/bin/env bash
# Starts the minimal ros2_control mock system in the background and returns.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash

nohup ros2 launch "$DIR/bringup.launch.py" > "$DIR/bringup.log" 2>&1 &
disown

echo "bringup started in background (pid $!), logs at $DIR/bringup.log"
