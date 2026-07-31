#!/usr/bin/env python3
import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

HEARTBEAT_PERIOD_SEC = 0.1
NUM_RESULTS_TO_EXIT = 5


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')
        # Reentrant group lets the timer keep firing on another executor
        # thread while a /slow_check call triggered from the tick callback
        # is still in flight.
        self._cb_group = ReentrantCallbackGroup()

        self._beat_count = 0
        self._result_count = 0
        self._result_lock = threading.Lock()
        self._done_event = threading.Event()

        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._heartbeat_timer = self.create_timer(
            HEARTBEAT_PERIOD_SEC, self._heartbeat_callback,
            callback_group=self._cb_group)

        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_callback, 10,
            callback_group=self._cb_group)

        self._slow_check_client = self.create_client(
            Trigger, '/slow_check', callback_group=self._cb_group)

    def _heartbeat_callback(self):
        msg = Int32()
        msg.data = self._beat_count
        self._beat_count += 1
        self._heartbeat_pub.publish(msg)

    def _tick_callback(self, msg):
        # call_async returns immediately, so this callback never blocks
        # the executor while waiting for the ~1s /slow_check response.
        if not self._slow_check_client.service_is_ready():
            self.get_logger().warn('/slow_check not ready, dropping tick')
            return
        future = self._slow_check_client.call_async(Trigger.Request())
        future.add_done_callback(self._slow_check_done)

    def _slow_check_done(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            return

        with self._result_lock:
            self._result_count += 1
            n = self._result_count
            reached_limit = self._result_count >= NUM_RESULTS_TO_EXIT

        self.get_logger().info(f'RESULT {n} {response.success}')

        if reached_limit:
            self._done_event.set()

    def wait_for_done(self):
        self._done_event.wait()


def main():
    rclpy.init()
    node = HeartbeatNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        node.wait_for_done()
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
