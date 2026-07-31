#!/usr/bin/env python3
import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from std_msgs.msg import Int32
from std_srvs.srv import Trigger


class HeartbeatNode(Node):
    MAX_RESULTS = 5
    HEARTBEAT_PERIOD = 0.1  # 10 Hz

    def __init__(self):
        super().__init__('heartbeat_node')

        # Separate reentrant groups so the heartbeat timer, the /tick
        # subscription, and pending service responses can all run
        # concurrently instead of blocking one another.
        timer_group = ReentrantCallbackGroup()
        sub_group = ReentrantCallbackGroup()
        client_group = ReentrantCallbackGroup()

        self._heartbeat_count = 0
        self._result_count = 0
        self.done_event = threading.Event()

        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._timer = self.create_timer(
            self.HEARTBEAT_PERIOD, self._publish_heartbeat, callback_group=timer_group)

        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_callback, 10, callback_group=sub_group)

        self._slow_check_client = self.create_client(
            Trigger, '/slow_check', callback_group=client_group)

    def _publish_heartbeat(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self._heartbeat_pub.publish(msg)

    def _tick_callback(self, msg):
        n = msg.data
        # call_async returns immediately; the response is handled later by
        # a done-callback, so this never blocks the heartbeat timer.
        future = self._slow_check_client.call_async(Trigger.Request())
        future.add_done_callback(lambda fut, n=n: self._handle_response(n, fut))

    def _handle_response(self, n, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'/slow_check call for tick {n} failed: {exc}')
            return

        self.get_logger().info(f'RESULT {n} {response.success}')

        self._result_count += 1
        if self._result_count >= self.MAX_RESULTS:
            self.done_event.set()


def main():
    rclpy.init()
    node = HeartbeatNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    node.done_event.wait()

    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
