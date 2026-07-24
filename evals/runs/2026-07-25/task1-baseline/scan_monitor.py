#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanMonitor(Node):

    def __init__(self):
        super().__init__('scan_monitor')
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10)

    def scan_callback(self, msg):
        valid_ranges = [r for r in msg.ranges if math.isfinite(r)]
        if not valid_ranges:
            self.get_logger().info(
                'No valid range readings in /scan message',
                throttle_duration_sec=1.0)
            return

        min_range = min(valid_ranges)
        self.get_logger().info(
            f'Minimum range: {min_range:.3f} m',
            throttle_duration_sec=1.0)


def main(args=None):
    rclpy.init(args=args)
    node = ScanMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
