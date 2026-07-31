#!/usr/bin/env bash
# Scenario for the ros2-dev ladder, rung L3.
#
#   ./dev3_scenario.sh up
#
# The prompt tells the cell that a `/scan` and the `map -> odom -> base_link ->
# laser_frame` chain "are already being published by someone else", so they must
# be up DURING the cell, not only when the checker runs. Making that sentence
# false is the mistake qos1 paid for: cells ran `ros2 topic info` on a topic that
# did not exist and had to guess.
#
# What is published:
#   /scan                 sensor_msgs/msg/LaserScan, 5 Hz, frame `laser_frame`
#                         360 samples, all finite, a solid return at 1.0 m in a
#                         30-degree arc dead ahead so the costmap has something
#                         unambiguous to mark.
#   TF  map -> odom       identity, static
#       odom -> base_link identity, dynamic at 20 Hz (Nav2 needs it non-stale)
#       base_link -> laser_frame  (0.2, 0, 0.1), static
#
# The scan is deliberately NOT all-max-range: a costmap wired correctly but fed
# an empty scan produces no cell above 250 and would look identical to a costmap
# that was never wired at all.
set -uo pipefail

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

PIDS=()
cleanup() {
  [ ${#PIDS[@]} -eq 0 ] || kill -9 "${PIDS[@]}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 - <<'PYEOF' &
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

N = 360
SCAN_HZ = 5.0
TF_HZ = 20.0


def tf(parent, child, x=0.0, y=0.0, z=0.0):
    t = TransformStamped()
    t.header.frame_id = parent
    t.child_frame_id = child
    t.transform.translation.x = x
    t.transform.translation.y = y
    t.transform.translation.z = z
    t.transform.rotation.w = 1.0
    return t


class Scenario(Node):
    def __init__(self):
        super().__init__("dev3_scenario")
        # Sensor QoS: this is what a real driver offers, and Nav2's observation
        # source expects it.
        qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.scan_pub = self.create_publisher(LaserScan, "/scan", qos)

        self.static_br = StaticTransformBroadcaster(self)
        self.static_br.sendTransform([
            tf("map", "odom"),
            tf("base_link", "laser_frame", 0.2, 0.0, 0.1),
        ])

        self.br = TransformBroadcaster(self)
        self.create_timer(1.0 / TF_HZ, self.pub_tf)
        self.create_timer(1.0 / SCAN_HZ, self.pub_scan)
        self.get_logger().info(
            "/scan 5 Hz 360 samples in laser_frame | "
            "map->odom->base_link->laser_frame up")

    def pub_tf(self):
        t = tf("odom", "base_link")
        t.header.stamp = self.get_clock().now().to_msg()
        self.br.sendTransform(t)

    def pub_scan(self):
        m = LaserScan()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = "laser_frame"
        m.angle_min = -math.pi
        m.angle_max = math.pi
        m.angle_increment = 2.0 * math.pi / N
        m.range_min = 0.05
        m.range_max = 10.0
        m.scan_time = 1.0 / SCAN_HZ
        m.time_increment = 0.0
        # Everything at 5 m, except a wall at 1 m in a 30-degree arc ahead.
        ranges = [5.0] * N
        centre = N // 2          # angle 0 == straight ahead
        half = int((15.0 / 360.0) * N)
        for i in range(centre - half, centre + half):
            ranges[i % N] = 1.0
        m.ranges = ranges
        self.scan_pub.publish(m)


rclpy.init()
node = Scenario()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
finally:
    if rclpy.ok():
        node.destroy_node()
        rclpy.shutdown()
PYEOF
PIDS+=($!)

wait
