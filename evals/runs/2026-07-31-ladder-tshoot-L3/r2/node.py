#!/usr/bin/env python3
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger

NUM_CALLS = 5


class ConcurrentCaller(Node):
    def __init__(self):
        super().__init__('concurrent_caller')

        # Reentrant group lets the 5 service-response callbacks run
        # concurrently (across executor worker threads) instead of being
        # serialized behind each other or behind the timer callback.
        client_group = ReentrantCallbackGroup()
        self.client = self.create_client(Trigger, '/slow_check', callback_group=client_group)
        self.get_logger().info('Waiting for /slow_check service...')
        self.client.wait_for_service()

        self.finished = threading.Event()
        self._started = False
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if self._started:
            return
        self._started = True
        self.timer.cancel()

        start = time.monotonic()
        futures = [self.client.call_async(Trigger.Request()) for _ in range(NUM_CALLS)]

        remaining = [len(futures)]
        lock = threading.Lock()
        all_done = threading.Event()

        def on_done(_future):
            with lock:
                remaining[0] -= 1
                if remaining[0] == 0:
                    all_done.set()

        for future in futures:
            future.add_done_callback(on_done)

        all_done.wait(timeout=10.0)
        elapsed = time.monotonic() - start

        for i, future in enumerate(futures, start=1):
            exc = future.exception()
            if exc is not None:
                self.get_logger().info(f'RESULT {i} False')
            else:
                self.get_logger().info(f'RESULT {i} {future.result().success}')

        self.get_logger().info(f'TOTAL {elapsed:.3f}')
        self.finished.set()


def main():
    rclpy.init()
    node = ConcurrentCaller()
    # One thread for the timer callback plus enough threads for all
    # concurrent service-response callbacks to be dispatched at once.
    executor = MultiThreadedExecutor(num_threads=NUM_CALLS + 2)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    node.finished.wait()

    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
