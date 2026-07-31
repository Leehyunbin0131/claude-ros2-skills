#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

HEARTBEAT_HZ = 10.0
MAX_RESULTS = 5


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        self.heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self.heartbeat_count = 0
        self.timer = self.create_timer(1.0 / HEARTBEAT_HZ, self.publish_heartbeat)

        self.cli = self.create_client(Trigger, '/slow_check')
        self.get_logger().info('Waiting for /slow_check service...')
        self.cli.wait_for_service()
        self.get_logger().info('/slow_check service is available')

        self.tick_sub = self.create_subscription(
            Int32, '/tick', self.tick_callback, 10)

        self.result_count = 0

    def publish_heartbeat(self):
        msg = Int32()
        msg.data = self.heartbeat_count
        self.heartbeat_pub.publish(msg)
        self.heartbeat_count += 1

    def tick_callback(self, msg):
        # Non-blocking call: does not stall the timer/heartbeat while the
        # 1s /slow_check response is pending.
        future = self.cli.call_async(Trigger.Request())
        future.add_done_callback(
            lambda f, n=msg.data: self.handle_response(n, f))

    def handle_response(self, n, future):
        try:
            response = future.result()
            success = response.success
        except Exception as e:
            self.get_logger().error(f'Service call for tick {n} failed: {e}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')
        self.result_count += 1

        if self.result_count >= MAX_RESULTS:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = HeartbeatNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
