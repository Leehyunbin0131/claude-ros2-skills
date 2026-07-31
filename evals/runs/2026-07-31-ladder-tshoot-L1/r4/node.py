#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.cli = self.create_client(Trigger, '/slow_check')
        self.result_count = 0
        self.done = False
        self.pending_future = None
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        # Skip this tick if the previous call hasn't finished yet.
        if self.pending_future is not None and not self.pending_future.done():
            return
        req = Trigger.Request()
        self.pending_future = self.cli.call_async(req)
        self.pending_future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        self.result_count += 1
        try:
            response = future.result()
            success = response.success
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
            success = False

        self.get_logger().info(f'RESULT {self.result_count} {success}')

        if self.result_count >= 5:
            self.timer.cancel()
            self.done = True


def main(args=None):
    rclpy.init(args=args)
    node = SlowCheckClient()

    node.cli.wait_for_service()

    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
