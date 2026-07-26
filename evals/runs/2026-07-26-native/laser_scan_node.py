#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LaserScanSubscriber(Node):
    def __init__(self):
        super().__init__('laser_scan_subscriber')

        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        self.latest_scan = None
        self.create_timer(1.0, self.timer_callback)

        self.get_logger().info('LaserScan subscriber started, listening on /scan')

    def scan_callback(self, msg: LaserScan):
        self.latest_scan = msg

    def timer_callback(self):
        if self.latest_scan is not None:
            valid_ranges = [r for r in self.latest_scan.ranges
                          if r > 0 and r != float('inf')]

            if valid_ranges:
                min_range = min(valid_ranges)
                self.get_logger().info(f'Minimum range: {min_range:.4f} m')
            else:
                self.get_logger().warn('No valid range measurements')
        else:
            self.get_logger().warn('Awaiting first scan message...')


def main(args=None):
    rclpy.init(args=args)
    node = LaserScanSubscriber()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
