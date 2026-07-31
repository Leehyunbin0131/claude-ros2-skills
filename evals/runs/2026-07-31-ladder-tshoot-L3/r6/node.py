#!/usr/bin/env python3
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        cb_group = ReentrantCallbackGroup()
        self.cli = self.create_client(Trigger, '/slow_check', callback_group=cb_group)
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /slow_check service...')
        self._fired = False
        self.timer = self.create_timer(0.1, self.timer_callback, callback_group=cb_group)

    def timer_callback(self):
        if self._fired:
            return
        self._fired = True
        self.timer.cancel()

        start = time.monotonic()
        futures = [self.cli.call_async(Trigger.Request()) for _ in range(5)]

        while not all(f.done() for f in futures):
            time.sleep(0.005)

        for i, future in enumerate(futures, start=1):
            result = future.result()
            self.get_logger().info(f'RESULT {i} {result.success}')

        elapsed = time.monotonic() - start
        self.get_logger().info(f'TOTAL {elapsed:.3f}')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = SlowCheckClient()
    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)
    executor.spin()
    node.destroy_node()


if __name__ == '__main__':
    main()
