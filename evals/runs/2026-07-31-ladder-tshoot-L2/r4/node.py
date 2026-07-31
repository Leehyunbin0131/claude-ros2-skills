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
    HEARTBEAT_PERIOD_SEC = 0.1  # 10 Hz

    def __init__(self):
        super().__init__('heartbeat_node')

        # Separate groups so the heartbeat timer can run concurrently with
        # tick handling / service-response processing.
        timer_group = MutuallyExclusiveCallbackGroup()
        tick_group = ReentrantCallbackGroup()

        self._heartbeat_count = 0
        self._result_count = 0
        self._result_lock = threading.Lock()
        self.done_event = threading.Event()

        self.heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self.timer = self.create_timer(
            self.HEARTBEAT_PERIOD_SEC, self._heartbeat_cb, callback_group=timer_group
        )

        self.slow_check_client = self.create_client(
            Trigger, '/slow_check', callback_group=tick_group
        )
        self.get_logger().info('Waiting for /slow_check service...')
        self.slow_check_client.wait_for_service()
        self.get_logger().info('/slow_check service is available')

        self.tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_cb, 10, callback_group=tick_group
        )

    def _heartbeat_cb(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self.heartbeat_pub.publish(msg)

    def _tick_cb(self, msg: Int32):
        # Non-blocking: fires the request and returns immediately so the
        # heartbeat timer is never held up while the response is pending.
        request = Trigger.Request()
        future = self.slow_check_client.call_async(request)
        future.add_done_callback(
            lambda fut, n=msg.data: self._service_done_cb(fut, n)
        )

    def _service_done_cb(self, future, n):
        try:
            response = future.result()
            success = response.success
        except Exception as exc:
            self.get_logger().error(f'/slow_check call failed: {exc}')
            success = False

        self.get_logger().info(f'RESULT {n} {success}')

        with self._result_lock:
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
