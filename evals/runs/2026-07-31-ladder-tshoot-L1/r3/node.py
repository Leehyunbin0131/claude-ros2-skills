#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.cli = self.create_client(Trigger, '/slow_check')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /slow_check service...')

        self.results_logged = 0
        self.calls_sent = 0
        self.max_results = 5
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if self.calls_sent >= self.max_results:
            return
        self.calls_sent += 1
        future = self.cli.call_async(Trigger.Request())
        future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        try:
            response = future.result()
            success = response.success
        except Exception as e:
            self.get_logger().error(f'service call failed: {e}')
            success = False

        self.results_logged += 1
        self.get_logger().info(f'RESULT {self.results_logged} {success}')

        if self.results_logged >= self.max_results:
            self.timer.cancel()


def main():
    rclpy.init()
    node = SlowCheckClient()
    try:
        while rclpy.ok() and node.results_logged < node.max_results:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
