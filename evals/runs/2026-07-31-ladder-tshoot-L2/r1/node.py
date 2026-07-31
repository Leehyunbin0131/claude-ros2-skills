#!/usr/bin/env python3
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

HEARTBEAT_PERIOD_SEC = 0.1  # 10 Hz
MAX_RESULTS = 5


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        self.result_count = 0
        self.result_lock = threading.Lock()
        self.heartbeat_count = 0

        # Separate callback groups so the heartbeat timer, tick subscription,
        # and in-flight service responses can all run concurrently on a
        # MultiThreadedExecutor. The tick callback never blocks on the
        # service call (uses call_async + a done-callback), so the timer
        # is never held up regardless of grouping, but keeping them apart
        # gives extra headroom under a multithreaded executor.
        timer_group = MutuallyExclusiveCallbackGroup()
        tick_group = MutuallyExclusiveCallbackGroup()
        client_group = ReentrantCallbackGroup()

        self.heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self.timer = self.create_timer(
            HEARTBEAT_PERIOD_SEC, self.publish_heartbeat, callback_group=timer_group)

        self.cli = self.create_client(Trigger, '/slow_check', callback_group=client_group)
        if not self.cli.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('/slow_check service not available after 5s, continuing anyway')

        self.tick_sub = self.create_subscription(
            Int32, '/tick', self.tick_callback, 10, callback_group=tick_group)

    def publish_heartbeat(self):
        msg = Int32()
        msg.data = self.heartbeat_count
        self.heartbeat_count += 1
        self.heartbeat_pub.publish(msg)

    def tick_callback(self, msg):
        with self.result_lock:
            if self.result_count >= MAX_RESULTS:
                return

        if not self.cli.service_is_ready():
            self.get_logger().warn(f'/slow_check not ready, skipping tick {msg.data}')
            return

        req = Trigger.Request()
        future = self.cli.call_async(req)
        future.add_done_callback(lambda fut, n=msg.data: self.handle_response(n, fut))

    def handle_response(self, n, future):
        try:
            response = future.result()
            success = response.success
        except Exception as exc:
            self.get_logger().error(f'Service call for tick {n} raised: {exc}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')

        with self.result_lock:
            self.result_count += 1

    def done(self):
        with self.result_lock:
            return self.result_count >= MAX_RESULTS


def main():
    rclpy.init()
    node = HeartbeatNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        while rclpy.ok() and not node.done():
            time.sleep(0.02)
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
