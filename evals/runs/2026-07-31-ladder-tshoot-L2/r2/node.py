#!/usr/bin/env python3

import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Int32
from std_srvs.srv import Trigger


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        # The heartbeat timer gets its own exclusive group so nothing
        # (tick callbacks or in-flight service futures) can ever delay it.
        timer_group = MutuallyExclusiveCallbackGroup()
        # Tick callbacks and service-response callbacks share a reentrant
        # group so several /slow_check calls can be in flight at once
        # without blocking each other or the timer.
        client_group = ReentrantCallbackGroup()

        self._heartbeat_count = 0
        self._result_count = 0
        self._result_lock = threading.Lock()
        self.done = threading.Event()

        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._heartbeat_timer = self.create_timer(
            0.1, self._heartbeat_cb, callback_group=timer_group)

        self._client = self.create_client(
            Trigger, '/slow_check', callback_group=client_group)
        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_cb, 10, callback_group=client_group)

    def _heartbeat_cb(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self._heartbeat_pub.publish(msg)

    def _tick_cb(self, msg: Int32):
        # Fire-and-forget async call so this callback returns immediately
        # and never blocks the heartbeat timer thread while /slow_check
        # is taking its ~1s to respond.
        future = self._client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda fut, n=msg.data: self._on_result(n, fut))

    def _on_result(self, n, future):
        try:
            response = future.result()
            success = response.success
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')

        with self._result_lock:
            self._result_count += 1
            if self._result_count >= 5:
                self.done.set()


def main():
    rclpy.init()
    node = HeartbeatNode()

    if not node._client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error('/slow_check service not available')
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    node.done.wait()

    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
