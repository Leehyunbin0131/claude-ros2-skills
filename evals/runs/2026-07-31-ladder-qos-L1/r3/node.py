#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class SensorSubscriber(Node):
    def __init__(self):
        super().__init__('sensor_subscriber')
        self.count = 0
        self.subscription = self.create_subscription(
            Int32,
            '/sensor',
            self.listener_callback,
            10)

    def listener_callback(self, msg):
        self.get_logger().info(f'GOT {msg.data}')
        self.count += 1
        if self.count >= 20:
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = SensorSubscriber()
    rclpy.spin(node)
    node.destroy_node()


if __name__ == '__main__':
    main()
