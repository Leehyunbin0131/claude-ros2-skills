#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanLogger(Node):
    def __init__(self):
        super().__init__('scan_logger')

        self.latest_scan = None

        # Subscribe to /scan with sensor QoS
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos_profile_sensor_data
        )

        # Timer to log minimum range once per second
        self.timer = self.create_timer(1.0, self.log_min_range)

    def scan_callback(self, msg: LaserScan):
        self.latest_scan = msg

    def log_min_range(self):
        if self.latest_scan is None:
            self.get_logger().warn('No scan received yet')
            return

        # Find minimum range (filter out inf values)
        valid_ranges = [r for r in self.latest_scan.ranges if not float('inf') == r]

        if valid_ranges:
            min_range = min(valid_ranges)
            self.get_logger().info(f'Minimum range: {min_range:.3f} m')
        else:
            self.get_logger().warn('No valid ranges in scan')


def main(args=None):
    rclpy.init(args=args)
    node = ScanLogger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
