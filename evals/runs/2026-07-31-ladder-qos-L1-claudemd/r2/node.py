#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32


class SensorSubscriber(Node):
    def __init__(self):
        super().__init__('sensor_subscriber')
        self.count = 0
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Int32, '/sensor', self.callback, qos)

    def callback(self, msg):
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
    sys.exit(0)


if __name__ == '__main__':
    main()
