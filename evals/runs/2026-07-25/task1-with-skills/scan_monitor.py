#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanMonitor(Node):

    def __init__(self):
        super().__init__('scan_monitor')
        self._latest_scan = None
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self._scan_callback,
            qos_profile_sensor_data,
        )
        self.timer = self.create_timer(1.0, self._log_min_range)

    def _scan_callback(self, msg):
        self._latest_scan = msg

    def _log_min_range(self):
        if self._latest_scan is None:
            self.get_logger().info('No scan received yet')
            return

        valid_ranges = [
            r for r in self._latest_scan.ranges
            if math.isfinite(r) and self._latest_scan.range_min <= r <= self._latest_scan.range_max
        ]

        if not valid_ranges:
            self.get_logger().info('No valid ranges in latest scan')
            return

        self.get_logger().info(f'Minimum range: {min(valid_ranges):.3f} m')


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
