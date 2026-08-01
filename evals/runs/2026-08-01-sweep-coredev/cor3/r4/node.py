#!/usr/bin/env python3
"""Lifecycle node 'counter': publishes an incrementing Int32 on /count at 10 Hz
while (and only while) it is in the ACTIVE state."""

import rclpy
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._count = 0
        self._pub = None
        self._timer = None
        self.get_logger().info('STATE unconfigured')

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._count = 0
        self._pub = self.create_lifecycle_publisher(Int32, '/count', 10)
        self._timer = self.create_timer(1.0 / 10.0, self._on_timer)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        ret = super().on_activate(state)
        self.get_logger().info('STATE active')
        return ret

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        ret = super().on_deactivate(state)
        self.get_logger().info('STATE inactive')
        return ret

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE errorprocessing')
        return TransitionCallbackReturn.SUCCESS

    def _destroy_timer_and_publisher(self):
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_lifecycle_publisher(self._pub)
            self._pub = None

    def _on_timer(self):
        # LifecyclePublisher.publish() is a no-op unless the node is active,
        # so nothing is emitted while unconfigured or inactive.
        if self._pub is None or not self._pub.is_activated:
            return
        msg = Int32()
        msg.data = self._count
        self._pub.publish(msg)
        self._count += 1


def main(args=None):
    rclpy.init(args=args)
    node = CounterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
