#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger


class ConcurrentCaller(Node):
    def __init__(self):
        super().__init__('concurrent_caller')
        self.group = ReentrantCallbackGroup()
        self.cli = self.create_client(
            Trigger, '/slow_check', callback_group=self.group)
        self.done = False
        self.timer = self.create_timer(
            0.1, self.timer_callback, callback_group=self.group)

    def timer_callback(self):
        # Only run once.
        self.timer.cancel()

        if not self.cli.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('/slow_check service not available')
            self.done = True
            return

        start = time.monotonic()

        futures = [self.cli.call_async(Trigger.Request()) for _ in range(5)]

        # Busy-wait here; response callbacks run concurrently on other
        # executor threads because this node uses a ReentrantCallbackGroup.
        while not all(f.done() for f in futures):
            time.sleep(0.005)

        elapsed = time.monotonic() - start

        for i, future in enumerate(futures, start=1):
            result = future.result()
            self.get_logger().info(f'RESULT {i} {result.success}')

        self.get_logger().info(f'TOTAL {elapsed:.3f}')
        self.done = True


def main():
    rclpy.init()
    node = ConcurrentCaller()
    executor = MultiThreadedExecutor(num_threads=10)
    executor.add_node(node)

    try:
        while rclpy.ok() and not node.done:
            executor.spin_once(timeout_sec=0.1)
    finally:
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
