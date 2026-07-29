#!/usr/bin/env python3
import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class MinRangeLogger(Node):

    def __init__(self):
        super().__init__('min_range_logger')
        self._latest_min = None
        self.create_subscription(
            LaserScan, '/scan', self._scan_callback, qos_profile_sensor_data
        )
        self.create_timer(1.0, self._log_min_range)

    def _scan_callback(self, msg: LaserScan):
        valid_ranges = [
            r for r in msg.ranges
            if math.isfinite(r) and msg.range_min <= r <= msg.range_max
        ]
        self._latest_min = min(valid_ranges) if valid_ranges else None

    def _log_min_range(self):
        if self._latest_min is None:
            self.get_logger().info('No valid range readings yet')
        else:
            self.get_logger().info(f'Minimum range: {self._latest_min:.3f} m')


def main(args=None):
    rclpy.init(args=args)
    node = MinRangeLogger()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
