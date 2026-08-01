#!/usr/bin/env python3
"""Lifecycle node 'counter' that publishes std_msgs/Int32 on /count at 10 Hz,
but only while ACTIVE."""

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.lifecycle import Node as LifecycleNode
from rclpy.lifecycle import State, TransitionCallbackReturn
from std_msgs.msg import Int32

PERIOD = 1.0 / 10.0  # 10 Hz


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._pub = None
        self._timer = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')

    def _timer_callback(self):
        if self._pub is not None and self._pub.is_activated:
            msg = Int32()
            msg.data = self._count
            self._count += 1
            self._pub.publish(msg)

    # -- lifecycle transitions --------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(Int32, '/count', 10)
        self._timer = self.create_timer(PERIOD, self._timer_callback)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        ret = super().on_activate(state)
        self.get_logger().info('STATE active')
        return ret

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        ret = super().on_deactivate(state)
        self.get_logger().info('STATE inactive')
        return ret

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_publisher(self._pub)
            self._pub = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_publisher(self._pub)
            self._pub = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: State) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_publisher(self._pub)
            self._pub = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS


def main(args=None):
    rclpy.init(args=args)
    node = CounterNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
