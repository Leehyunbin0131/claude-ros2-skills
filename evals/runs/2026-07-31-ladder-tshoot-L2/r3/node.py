#!/usr/bin/env python3
import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

from std_msgs.msg import Int32
from std_srvs.srv import Trigger

HEARTBEAT_PERIOD_SEC = 0.1
MAX_RESULTS = 5


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        # Separate callback groups so the timer and the (non-blocking) tick
        # subscription never wait on each other, and so multiple in-flight
        # service calls can be handled concurrently.
        timer_group = MutuallyExclusiveCallbackGroup()
        tick_group = MutuallyExclusiveCallbackGroup()
        client_group = ReentrantCallbackGroup()

        self._heartbeat_count = 0
        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._timer = self.create_timer(
            HEARTBEAT_PERIOD_SEC, self._on_timer, callback_group=timer_group)

        self._client = self.create_client(
            Trigger, '/slow_check', callback_group=client_group)

        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._on_tick, 10, callback_group=tick_group)

        self._result_count = 0
        self._lock = threading.Lock()

    def _on_timer(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self._heartbeat_pub.publish(msg)

    def _on_tick(self, msg: Int32):
        # call_async returns immediately; the ~1s service latency is
        # absorbed by the executor's other threads, so this callback
        # never blocks the heartbeat timer.
        if not self._client.service_is_ready():
            self.get_logger().warn('/slow_check not available, skipping tick')
            return
        future = self._client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda f, n=msg.data: self._on_response(n, f))

    def _on_response(self, n, future):
        try:
            success = future.result().success
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')

        with self._lock:
            self._result_count += 1
            done = self._result_count >= MAX_RESULTS

        if done:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = HeartbeatNode()
    executor = MultiThreadedExecutor(num_threads=4)

    try:
        rclpy.spin(node, executor=executor)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
