#!/usr/bin/env python3
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger

NUM_CALLS = 5


class ConcurrentCallerNode(Node):
    def __init__(self):
        super().__init__('concurrent_caller')
        self.cb_group = ReentrantCallbackGroup()
        self.client = self.create_client(
            Trigger, '/slow_check', callback_group=self.cb_group
        )
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /slow_check service...')

        self._fired = False
        self.timer = self.create_timer(
            1.0, self.timer_callback, callback_group=self.cb_group
        )

    def timer_callback(self):
        if self._fired:
            return
        self._fired = True
        self.timer.cancel()

        start = time.monotonic()

        futures = [self.client.call_async(Trigger.Request()) for _ in range(NUM_CALLS)]

        while not all(f.done() for f in futures):
            time.sleep(0.005)

        for i, future in enumerate(futures, start=1):
            result = future.result()
            self.get_logger().info(f'RESULT {i} {result.success}')

        elapsed = time.monotonic() - start
        self.get_logger().info(f'TOTAL {elapsed}')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = ConcurrentCallerNode()
    executor = MultiThreadedExecutor(num_threads=NUM_CALLS + 2)
    executor.add_node(node)
    try:
        executor.spin()
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
