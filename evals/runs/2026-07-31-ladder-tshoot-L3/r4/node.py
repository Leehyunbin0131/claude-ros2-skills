#!/usr/bin/env python3
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger


class ConcurrentCaller(Node):
    def __init__(self):
        super().__init__('concurrent_caller')
        # A single reentrant group lets the timer callback and the five
        # service-response callbacks all run concurrently on the
        # MultiThreadedExecutor's worker threads instead of serializing.
        cb_group = ReentrantCallbackGroup()
        self.cli = self.create_client(Trigger, '/slow_check', callback_group=cb_group)
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /slow_check service...')
        self.finished = False
        self.timer = self.create_timer(1.0, self.timer_callback, callback_group=cb_group)

    def timer_callback(self):
        self.timer.cancel()

        start = time.monotonic()

        # Dispatch all five requests before waiting on any of them so they
        # are in flight concurrently rather than one-at-a-time.
        futures = [self.cli.call_async(Trigger.Request()) for _ in range(5)]

        while not all(f.done() for f in futures):
            time.sleep(0.005)

        elapsed = time.monotonic() - start

        for i, future in enumerate(futures, start=1):
            response = future.result()
            self.get_logger().info(f'RESULT {i} {response.success}')

        self.get_logger().info(f'TOTAL {elapsed:.3f}')

        self.finished = True


def main():
    rclpy.init()
    node = ConcurrentCaller()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        while rclpy.ok() and not node.finished:
            executor.spin_once(timeout_sec=0.1)
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
