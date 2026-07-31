#!/usr/bin/env python3
import sys
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger


class ConcurrentTriggerNode(Node):
    def __init__(self):
        super().__init__('concurrent_slow_check_node')
        self.cb_group = ReentrantCallbackGroup()
        self.client = self.create_client(
            Trigger, '/slow_check', callback_group=self.cb_group
        )
        self._fired = False
        self.timer = self.create_timer(
            0.5, self.timer_callback, callback_group=self.cb_group
        )

    def timer_callback(self):
        if self._fired:
            return
        self._fired = True
        self.timer.cancel()

        if not self.client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('/slow_check service not available')
            rclpy.shutdown()
            return

        start = time.time()

        # Fire all five requests concurrently before waiting on any of them.
        futures = [self.client.call_async(Trigger.Request()) for _ in range(5)]

        events = [threading.Event() for _ in futures]
        for fut, ev in zip(futures, events):
            fut.add_done_callback(lambda _f, ev=ev: ev.set())

        # Blocking here only ties up this one worker thread; the
        # ReentrantCallbackGroup + MultiThreadedExecutor lets the other
        # in-flight service responses be processed concurrently.
        for ev in events:
            ev.wait()

        for i, fut in enumerate(futures, start=1):
            response = fut.result()
            self.get_logger().info(f'RESULT {i} {response.success}')

        elapsed = time.time() - start
        self.get_logger().info(f'TOTAL {elapsed:.3f}')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = ConcurrentTriggerNode()
    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)
    try:
        executor.spin()
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()

    sys.exit(0)


if __name__ == '__main__':
    main()
