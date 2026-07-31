#!/usr/bin/env python3
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import Trigger


class ConcurrentCaller(Node):
    def __init__(self):
        super().__init__('concurrent_caller')
        self.cb_group = ReentrantCallbackGroup()
        self.client = self.create_client(
            Trigger, '/slow_check', callback_group=self.cb_group)
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /slow_check service...')

        self._fired = False
        self.timer = self.create_timer(
            0.5, self.timer_callback, callback_group=self.cb_group)

    def timer_callback(self):
        # Only run the batch once.
        if self._fired:
            return
        self._fired = True
        self.timer.cancel()

        start = time.monotonic()

        # Fire all five requests back-to-back so they are in flight
        # concurrently, then wait for all of them to complete.
        futures = [self.client.call_async(Trigger.Request()) for _ in range(5)]

        while not all(f.done() for f in futures):
            time.sleep(0.005)

        elapsed = time.monotonic() - start

        for i, future in enumerate(futures, start=1):
            result = future.result()
            self.get_logger().info(f'RESULT {i} {result.success}')

        self.get_logger().info(f'TOTAL {elapsed:.3f}')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = ConcurrentCaller()
    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)
    try:
        executor.spin()
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
