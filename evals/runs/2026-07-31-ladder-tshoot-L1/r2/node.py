#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.client = self.create_client(Trigger, '/slow_check')
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /slow_check service...')
        self.result_count = 0
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        request = Trigger.Request()
        future = self.client.call_async(request)
        future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
            return
        self.result_count += 1
        self.get_logger().info(f'RESULT {self.result_count} {response.success}')
        if self.result_count >= 5:
            self.timer.cancel()


def main(args=None):
    rclpy.init(args=args)
    node = SlowCheckClient()
    try:
        while rclpy.ok() and node.result_count < 5:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
