#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from std_msgs.msg import Int32


class SensorSubscriber(Node):
    def __init__(self):
        super().__init__('sensor_subscriber')
        self.count = 0
        qos_profile = QoSProfile(
            depth=10,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )
        self.subscription = self.create_subscription(
            Int32,
            '/sensor',
            self.listener_callback,
            qos_profile,
        )

    def listener_callback(self, msg):
        self.get_logger().info(f'GOT {msg.data}')
        self.count += 1
        if self.count >= 20:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = SensorSubscriber()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
