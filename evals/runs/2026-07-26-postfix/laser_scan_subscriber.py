#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LaserScanSubscriber(Node):
    def __init__(self):
        super().__init__('laser_scan_subscriber')

        # Subscribe to the scan topic
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        # Store the latest minimum range
        self.min_range = None

        # Create a timer to log once per second
        self.timer = self.create_timer(1.0, self.log_min_range)

    def scan_callback(self, msg: LaserScan):
        """Callback for incoming LaserScan messages."""
        # Filter out invalid ranges (zeros, infinities, NaNs)
        valid_ranges = [r for r in msg.ranges if r > 0 and r < float('inf')]

        if valid_ranges:
            self.min_range = min(valid_ranges)

    def log_min_range(self):
        """Log the minimum range once per second."""
        if self.min_range is not None:
            self.get_logger().info(f'Minimum range: {self.min_range:.4f} m')
        else:
            self.get_logger().info('No valid scan data received yet')


def main(args=None):
    rclpy.init(args=args)
    node = LaserScanSubscriber()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
