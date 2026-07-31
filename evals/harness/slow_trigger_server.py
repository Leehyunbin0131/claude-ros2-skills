#!/usr/bin/env python3
"""Scenario for the ros2-troubleshooting executor ladder: a service that is slow
on purpose.

`/slow_check` (`std_srvs/srv/Trigger`) sleeps ~1 s before responding. That delay
is the whole point: it makes the single-threaded-executor deadlock observable in
wall time instead of being a race. A client that calls
`spin_until_future_complete()` from inside its own callback, on a
SingleThreadedExecutor, blocks the executor that has to deliver the response --
so the future never completes and the node hangs forever rather than "sometimes".

Runs a MultiThreadedExecutor itself so the server is never the bottleneck: any
hang observed in a cell belongs to the cell.
"""
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger

DELAY_S = 1.0


class SlowTrigger(Node):
    def __init__(self):
        super().__init__("slow_trigger_server")
        self._n = 0
        self.srv = self.create_service(
            Trigger, "/slow_check", self.on_trigger,
            callback_group=ReentrantCallbackGroup())
        self.get_logger().info(f"/slow_check up, {DELAY_S}s delay per call")

    # NOT named `handle`: rclpy.node.Node already has a `handle` property, and
    # shadowing it with a service callback makes Node.__init__ fail with
    # "TypeError: 'method' object does not support the context manager protocol"
    # from `with self.handle:` -- the server then never starts at all.
    def on_trigger(self, request, response):
        time.sleep(DELAY_S)
        self._n += 1
        response.success = True
        response.message = f"ok {self._n}"
        return response


def main():
    rclpy.init()
    node = SlowTrigger()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    try:
        ex.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
