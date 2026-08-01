#!/usr/bin/env python3
"""Lifecycle node 'counter' that publishes an incrementing Int32 on /count at 10 Hz
while active. See on_* callbacks below for state transition handling."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._publisher = None
        self._timer = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._publisher = self.create_lifecycle_publisher(Int32, '/count', 10)
        self._count = 0
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        ret = super().on_activate(state)
        if ret != TransitionCallbackReturn.SUCCESS:
            return ret
        self._timer = self.create_timer(0.1, self._on_timer)
        self.get_logger().info('STATE active')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        ret = super().on_deactivate(state)
        if ret != TransitionCallbackReturn.SUCCESS:
            return ret
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def _on_timer(self):
        if self._publisher is None or not self._publisher.is_activated:
            return
        msg = Int32()
        msg.data = self._count
        self._publisher.publish(msg)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = CounterNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
