#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanMinRangeLogger(Node):
    def __init__(self):
        super().__init__('scan_min_range_logger')
        self.latest_scan = None

        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos_profile_sensor_data
        )

        self.timer = self.create_timer(1.0, self.log_min_range)

    def scan_callback(self, msg: LaserScan):
        self.latest_scan = msg

    def log_min_range(self):
        if self.latest_scan is None:
            return

        msg = self.latest_scan
        valid_ranges = [
            r for r in msg.ranges
            if math.isfinite(r) and msg.range_min <= r <= msg.range_max
        ]

        if valid_ranges:
            min_range = min(valid_ranges)
            self.get_logger().info(f'Minimum range: {min_range:.3f} m')
        else:
            self.get_logger().warn('No valid range readings in latest scan')


def main(args=None):
    rclpy.init(args=args)
    node = ScanMinRangeLogger()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
