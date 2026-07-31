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

    MAX_RESULTS = 5
    HEARTBEAT_PERIOD = 0.1  # 10 Hz

    def __init__(self):
        super().__init__('heartbeat_node')

        self._lock = threading.Lock()
        self._heartbeat_count = 0
        self._calls_started = 0
        self._results_received = 0
        self.done_event = threading.Event()

        # Separate callback groups so the timer, the /tick subscription and the
        # /slow_check response handling can all be dispatched concurrently by
        # the MultiThreadedExecutor -- an in-flight (~1s) service call must
        # never block the 10 Hz heartbeat timer.
        timer_group = MutuallyExclusiveCallbackGroup()
        tick_group = MutuallyExclusiveCallbackGroup()
        client_group = ReentrantCallbackGroup()

        self.heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self.timer = self.create_timer(
            self.HEARTBEAT_PERIOD, self._publish_heartbeat, callback_group=timer_group)

        self.tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_callback, 10, callback_group=tick_group)

        self.slow_check_client = self.create_client(
            Trigger, '/slow_check', callback_group=client_group)

    def _publish_heartbeat(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self.heartbeat_pub.publish(msg)
        self._heartbeat_count += 1

    def _tick_callback(self, msg: Int32):
        with self._lock:
            if self._calls_started >= self.MAX_RESULTS:
                return
            self._calls_started += 1

        n = msg.data
        if not self.slow_check_client.service_is_ready():
            self.get_logger().warn('/slow_check service not ready, skipping this tick')
            with self._lock:
                self._calls_started -= 1
            return

        request = Trigger.Request()
        future = self.slow_check_client.call_async(request)
        future.add_done_callback(lambda f, n=n: self._handle_response(n, f))

    def _handle_response(self, n, future):
        try:
            response = future.result()
            success = response.success
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')

        with self._lock:
            self._results_received += 1
            done = self._results_received >= self.MAX_RESULTS
        if done:
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
    spin_thread.join(timeout=2.0)
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
