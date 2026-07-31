#!/usr/bin/env python3
import sys
import threading
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_srvs.srv import Trigger

NUM_CALLS = 5


class ConcurrentCaller(Node):
    def __init__(self):
        super().__init__('concurrent_caller')
        self.client = self.create_client(Trigger, '/slow_check')
        self.timer = self.create_timer(1.0, self.on_timer)
        self._fired = False
        self._remaining = NUM_CALLS
        self._lock = threading.Lock()
        self._start = None

    def on_timer(self):
        if self._fired:
            return
        self._fired = True
        self.timer.cancel()

        if not self.client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error('/slow_check service not available')
            rclpy.shutdown()
            return

        self._start = time.monotonic()
        # Fire all requests back-to-back (call_async does not block on the
        # response), so all five are in flight concurrently before any
        # response is handled.
        for i in range(1, NUM_CALLS + 1):
            future = self.client.call_async(Trigger.Request())
            future.add_done_callback(self._make_callback(i))

    def _make_callback(self, call_num):
        def callback(future):
            try:
                success = future.result().success
            except Exception as exc:
                self.get_logger().error(f'call {call_num} raised: {exc}')
                success = False

            self.get_logger().info(f'RESULT {call_num} {success}')

            with self._lock:
                self._remaining -= 1
                finished = self._remaining == 0

            if finished:
                elapsed = time.monotonic() - self._start
                self.get_logger().info(f'TOTAL {elapsed:.3f}')
                rclpy.shutdown()

        return callback


def main():
    rclpy.init()
    node = ConcurrentCaller()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()

    sys.exit(0)


if __name__ == '__main__':
    main()
