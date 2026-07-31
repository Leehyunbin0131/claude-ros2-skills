#!/usr/bin/env python3
import os
import sys
import threading

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Int32
from std_srvs.srv import Trigger

RESULTS_NEEDED = 5


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        # Separate, non-exclusive groups so the heartbeat timer is never
        # blocked by /tick handling or by in-flight /slow_check calls.
        self._heartbeat_group = MutuallyExclusiveCallbackGroup()
        self._tick_group = MutuallyExclusiveCallbackGroup()
        self._service_group = ReentrantCallbackGroup()

        self._heartbeat_count = 0
        self._result_count = 0
        self._result_lock = threading.Lock()
        self.done_event = threading.Event()

        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._heartbeat_timer = self.create_timer(
            0.1, self._on_heartbeat, callback_group=self._heartbeat_group)

        self._client = self.create_client(
            Trigger, '/slow_check', callback_group=self._service_group)

        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._on_tick, 10, callback_group=self._tick_group)

    def _on_heartbeat(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self._heartbeat_pub.publish(msg)

    def _on_tick(self, msg: Int32):
        # call_async only enqueues the request; it returns immediately so
        # this callback (and therefore the heartbeat timer) never stalls
        # waiting on the ~1s /slow_check response.
        future = self._client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda f, n=msg.data: self._on_service_response(n, f))

    def _on_service_response(self, tick_value, future):
        try:
            response = future.result()
            success = response.success
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            success = False

        self.get_logger().info(f'RESULT {tick_value} {success}')

        with self._result_lock:
            self._result_count += 1
            reached_target = self._result_count >= RESULTS_NEEDED
        if reached_target:
            self.done_event.set()


def main():
    rclpy.init()
    node = HeartbeatNode()

    if not node._client.wait_for_service(timeout_sec=10.0):
        node.get_logger().error('/slow_check service not available')
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    executor = MultiThreadedExecutor(num_threads=max(8, (os.cpu_count() or 4)))
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        node.done_event.wait()
    except KeyboardInterrupt:
        pass

    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
