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
            self.get_logger().info('waiting for /slow_check service...')
        self.call_count = 0
        self.results_logged = 0
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if self.results_logged >= 5:
            return
        self.call_count += 1
        n = self.call_count
        future = self.client.call_async(Trigger.Request())
        future.add_done_callback(lambda fut, n=n: self.response_callback(fut, n))

    def response_callback(self, future, n):
        if self.results_logged >= 5:
            return
        try:
            response = future.result()
            success = response.success
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
            success = False
        self.get_logger().info(f'RESULT {n} {success}')
        self.results_logged += 1


def main():
    rclpy.init()
    node = SlowCheckClient()
    try:
        while rclpy.ok() and node.results_logged < 5:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
