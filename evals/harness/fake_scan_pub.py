#!/usr/bin/env python3
"""Stand-in for a real LiDAR driver: publishes /scan with sensor-data QoS.

Exists so Task 1 can be graded against a running system without a robot. Two
properties matter:

  * BEST_EFFORT/VOLATILE (`qos_profile_sensor_data`) — the same offer a real
    driver makes, so a default RELIABLE subscriber matches nothing and its
    callback never fires. That is the failure Task 1 is about.
  * The `ranges` array deliberately contains `inf`, `nan`, a below-`range_min`
    value and an above-`range_max` value, so a node that only filters with
    `isfinite` reports a wrong minimum instead of crashing.

Field names and the QoS profile were read from the installed Jazzy packages
(`ros2 interface show sensor_msgs/msg/LaserScan`, `rclpy.qos`).
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

RANGE_MIN = 0.12
RANGE_MAX = 12.0
TRUE_MIN = 0.45  # the answer a correct node must report


class FakeScan(Node):
    def __init__(self):
        super().__init__("fake_scan_pub")
        self.pub = self.create_publisher(LaserScan, "/scan", qos_profile_sensor_data)
        self.create_timer(1.0 / 5.0, self.tick)  # 5 Hz, like the TB3 sim
        self.get_logger().info(
            f"publishing /scan at 5 Hz (BEST_EFFORT); true in-bounds min = {TRUE_MIN} m")

    def tick(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_scan"
        msg.angle_min = -math.pi
        msg.angle_max = math.pi
        msg.angle_increment = 2.0 * math.pi / 12.0
        msg.time_increment = 0.0
        msg.scan_time = 0.2
        msg.range_min = RANGE_MIN
        msg.range_max = RANGE_MAX
        msg.ranges = [
            float("inf"),   # no return — must be ignored
            2.10,
            float("nan"),   # invalid — must be ignored
            0.02,           # BELOW range_min — must be ignored, not reported as min
            TRUE_MIN,       # the correct answer
            3.30,
            99.0,           # ABOVE range_max — must be ignored
            1.80,
            float("inf"),
            2.60,
            0.90,
            4.40,
        ]
        msg.intensities = []
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FakeScan()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
