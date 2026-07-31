#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32


class SensorLogger(Node):
    def __init__(self):
        super().__init__('sensor_logger')
        self.count = 0
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Int32, '/sensor', self.callback, qos)

    def callback(self, msg):
        self.count += 1
        self.get_logger().info(f'GOT {msg.data}')
        if self.count >= 20:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = SensorLogger()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
