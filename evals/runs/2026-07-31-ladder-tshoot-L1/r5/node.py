#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.client = self.create_client(Trigger, '/slow_check')
        self.count = 0
        self.pending = False
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if self.pending:
            return
        if not self.client.service_is_ready():
            self.get_logger().warn('/slow_check service not available yet')
            return
        self.pending = True
        future = self.client.call_async(Trigger.Request())
        future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        self.pending = False
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
            return
        self.count += 1
        self.get_logger().info(f'RESULT {self.count} {response.success}')


def main():
    rclpy.init()
    node = SlowCheckClient()

    node.get_logger().info('Waiting for /slow_check service...')
    node.client.wait_for_service()

    try:
        while rclpy.ok() and node.count < 5:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
