#!/usr/bin/env bash
# Bring up the Task 3 situation and leave it running: a BEST_EFFORT camera
# publisher at 30 Hz plus a default-RELIABLE subscriber that never receives.
#
# `ros2 topic hz /camera/image_raw` reports 30 Hz (the ros2cli subscriber
# negotiates a compatible profile), while reliable_image_sub keeps logging
# "images received: 0". Nothing errors. That is the whole bug.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

trap 'kill 0' EXIT INT TERM

python3 "$HERE/fake_camera_pub.py" &
python3 "$HERE/reliable_image_sub.py" &

echo "/camera/image_raw: BEST_EFFORT publisher + RELIABLE subscriber running."
echo "Ctrl-C to stop."
wait
