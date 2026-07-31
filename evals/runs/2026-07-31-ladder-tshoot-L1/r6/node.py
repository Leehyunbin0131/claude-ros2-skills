#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

NUM_RESULTS = 5


class SlowCheckClient(Node):
    def __init__(self):
        super().__init__('slow_check_client')
        self.cli = self.create_client(Trigger, '/slow_check')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for /slow_check service...')
        self.count = 0
        self.call_in_progress = False
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        if self.call_in_progress or self.count >= NUM_RESULTS:
            return
        self.call_in_progress = True
        future = self.cli.call_async(Trigger.Request())
        future.add_done_callback(self.response_callback)

    def response_callback(self, future):
        self.call_in_progress = False
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
            return
        self.count += 1
        self.get_logger().info(f'RESULT {self.count} {response.success}')


def main(args=None):
    rclpy.init(args=args)
    node = SlowCheckClient()
    try:
        while rclpy.ok() and node.count < NUM_RESULTS:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
