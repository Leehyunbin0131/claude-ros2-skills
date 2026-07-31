#!/usr/bin/env python3
import functools
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

NUM_CALLS = 5


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.client = self.create_client(Trigger, '/slow_check')
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /slow_check service...')

        self.done = False
        self.start_time = None
        self.remaining = NUM_CALLS
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        self.timer.cancel()
        self.start_time = time.monotonic()

        for i in range(NUM_CALLS):
            future = self.client.call_async(Trigger.Request())
            future.add_done_callback(functools.partial(self.response_callback, i + 1))

    def response_callback(self, n, future):
        response = future.result()
        self.get_logger().info(f'RESULT {n} {response.success}')

        self.remaining -= 1
        if self.remaining == 0:
            elapsed = time.monotonic() - self.start_time
            self.get_logger().info(f'TOTAL {elapsed:.3f}')
            self.done = True


def main():
    rclpy.init()
    node = SlowCheckClient()

    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
