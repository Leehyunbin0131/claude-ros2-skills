#!/usr/bin/env python3
"""Lifecycle node that publishes an incrementing Int32 on /count at 10 Hz,
but only while it is in the ACTIVE state."""

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.lifecycle import Node as LifecycleNode
from rclpy.lifecycle import State, TransitionCallbackReturn
from rclpy.timer import Timer

from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._count = 0
        self._pub = None
        self._timer: Timer = None
        self.get_logger().info('STATE unconfigured')

    def _publish(self):
        if self._pub is None or not self._pub.is_activated:
            return
        msg = Int32()
        msg.data = self._count
        self._pub.publish(msg)
        self._count += 1

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(Int32, '/count', 10)
        self._timer = self.create_timer(0.1, self._publish)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('STATE active')
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('STATE inactive')
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_lifecycle_publisher(self._pub)
            self._pub = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_lifecycle_publisher(self._pub)
            self._pub = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('STATE errorprocessing')
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_lifecycle_publisher(self._pub)
            self._pub = None
        return TransitionCallbackReturn.SUCCESS


def main(args=None):
    rclpy.init(args=args)
    executor = SingleThreadedExecutor()
    node = CounterNode()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
