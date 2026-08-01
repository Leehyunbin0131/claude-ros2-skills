#!/usr/bin/env python3
"""Lifecycle node 'counter' that publishes an incrementing Int32 on /count at 10 Hz while active."""

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.lifecycle import Node, Publisher, State, TransitionCallbackReturn
from rclpy.timer import Timer
from std_msgs.msg import Int32


class CounterNode(Node):

    def __init__(self):
        super().__init__('counter')
        self._pub: Publisher = None
        self._timer: Timer = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')

    def _tick(self):
        if self._pub is None or not self._pub.is_activated:
            return
        msg = Int32()
        msg.data = self._count
        self._count += 1
        self._pub.publish(msg)

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(Int32, '/count', 10)
        self._timer = self.create_timer(1.0 / 10.0, self._tick)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        result = super().on_activate(state)
        self.get_logger().info('STATE active')
        return result

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        result = super().on_deactivate(state)
        self.get_logger().info('STATE inactive')
        return result

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: State) -> TransitionCallbackReturn:
        self._destroy_timer_and_publisher()
        self.get_logger().info('STATE errorprocessing')
        return TransitionCallbackReturn.SUCCESS

    def _destroy_timer_and_publisher(self):
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._pub is not None:
            self.destroy_publisher(self._pub)
            self._pub = None


def main(args=None):
    rclpy.init(args=args)
    node = CounterNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
