#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.cli = self.create_client(Trigger, '/slow_check')
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.fired = False
        self.start_time = None
        self.done_count = 0
        self.total_calls = 5

    def timer_callback(self):
        if self.fired:
            return
        self.fired = True
        self.timer.cancel()

        if not self.cli.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('/slow_check service not available')
            rclpy.shutdown()
            return

        self.start_time = time.monotonic()
        for i in range(1, self.total_calls + 1):
            future = self.cli.call_async(Trigger.Request())
            future.add_done_callback(self._make_done_callback(i))

    def _make_done_callback(self, index):
        def _callback(future):
            try:
                response = future.result()
                success = response.success
            except Exception as exc:
                self.get_logger().error(f'RESULT {index} exception: {exc}')
                success = False
            self.get_logger().info(f'RESULT {index} {success}')

            self.done_count += 1
            if self.done_count == self.total_calls:
                elapsed = time.monotonic() - self.start_time
                self.get_logger().info(f'TOTAL {elapsed:.3f}')
                rclpy.shutdown()
        return _callback


def main():
    rclpy.init()
    node = SlowCheckClient()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
