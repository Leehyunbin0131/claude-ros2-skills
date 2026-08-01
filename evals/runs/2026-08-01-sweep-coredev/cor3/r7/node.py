#!/usr/bin/env python3
"""Lifecycle node 'counter' that publishes an incrementing Int32 on /count at 10 Hz
while active. Nothing is published while unconfigured or inactive."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._count = 0
        self._publisher = None
        self._timer = None

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._publisher = self.create_lifecycle_publisher(Int32, '/count', 10)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._timer = self.create_timer(0.1, self._on_timer)
        self.get_logger().info('STATE active')
        return super().on_activate(state)

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self._timer.cancel()
            self.destroy_timer(self._timer)
            self._timer = None
        self.get_logger().info('STATE inactive')
        return super().on_deactivate(state)

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self._timer.cancel()
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.get_logger().info('STATE errorprocessing')
        return TransitionCallbackReturn.SUCCESS

    def _on_timer(self):
        msg = Int32()
        msg.data = self._count
        self._count += 1
        # LifecyclePublisher.publish() is a no-op unless the node is active,
        # so this is safe even if a stray timer callback fires mid-transition.
        self._publisher.publish(msg)


def main():
    rclpy.init()
    node = CounterNode()
    node.get_logger().info('STATE unconfigured')
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
