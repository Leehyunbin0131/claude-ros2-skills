#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan


class MinRangeLogger(Node):

    def __init__(self):
        super().__init__('min_range_logger')

        scan_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=5,
        )

        self._latest_min_range = None
        self.subscription = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, scan_qos
        )
        self.timer = self.create_timer(1.0, self.timer_callback)

    def scan_callback(self, msg: LaserScan):
        valid_ranges = [
            r for r in msg.ranges
            if math.isfinite(r) and msg.range_min <= r <= msg.range_max
        ]
        self._latest_min_range = min(valid_ranges) if valid_ranges else None

    def timer_callback(self):
        if self._latest_min_range is None:
            self.get_logger().info('No valid range readings yet')
        else:
            self.get_logger().info(f'Min range: {self._latest_min_range:.3f} m')


def main(args=None):
    rclpy.init(args=args)
    node = MinRangeLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
