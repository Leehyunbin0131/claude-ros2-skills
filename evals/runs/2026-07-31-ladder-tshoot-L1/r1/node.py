#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.client = self.create_client(Trigger, '/slow_check')
        self.result_count = 0
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if not self.client.service_is_ready():
            self.get_logger().warn('/slow_check service not available yet')
            return
        future = self.client.call_async(Trigger.Request())
        future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        response = future.result()
        self.result_count += 1
        self.get_logger().info(f'RESULT {self.result_count} {response.success}')
        if self.result_count >= 5:
            self.timer.cancel()


def main():
    rclpy.init()
    node = SlowCheckClient()

    while not node.client.wait_for_service(timeout_sec=1.0):
        node.get_logger().info('Waiting for /slow_check service...')

    try:
        while node.result_count < 5:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
