#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_msgs.msg import Int32
from std_srvs.srv import Trigger


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__('heartbeat_node')

        self._heartbeat_count = 0
        self.result_count = 0
        self._target_results = 5

        # A single reentrant group so the /tick callback awaiting the service
        # response never blocks (or is blocked by) the heartbeat timer or the
        # service response callback: a MutuallyExclusiveCallbackGroup would
        # keep the /tick callback "active" for the whole await, deadlocking
        # the client's own response processing and stalling the timer.
        cb_group = ReentrantCallbackGroup()

        self._heartbeat_pub = self.create_publisher(Int32, '/heartbeat', 10)
        self._heartbeat_timer = self.create_timer(
            0.1, self._publish_heartbeat, callback_group=cb_group)

        self._slow_check_client = self.create_client(
            Trigger, '/slow_check', callback_group=cb_group)

        self._tick_sub = self.create_subscription(
            Int32, '/tick', self._tick_callback, 10, callback_group=cb_group)

    def _publish_heartbeat(self):
        msg = Int32()
        msg.data = self._heartbeat_count
        self._heartbeat_count += 1
        self._heartbeat_pub.publish(msg)

    async def _tick_callback(self, msg):
        request = Trigger.Request()
        response = await self._slow_check_client.call_async(request)

        self.result_count += 1
        self.get_logger().info(f'RESULT {self.result_count} {response.success}')


def main():
    rclpy.init()
    node = HeartbeatNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    try:
        while rclpy.ok() and node.result_count < node._target_results:
            executor.spin_once(timeout_sec=0.01)
    finally:
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
