#!/usr/bin/env python3

import rclpy
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._publisher = None
        self._timer = None
        self._count = 0
        self.get_logger().info('STATE unconfigured')

    def _timer_callback(self):
        msg = Int32()
        msg.data = self._count
        self._count += 1
        self._publisher.publish(msg)

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._publisher = self.create_publisher(Int32, '/count', 10)
        self._count = 0
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._timer = self.create_timer(0.1, self._timer_callback)
        self.get_logger().info('STATE active')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: LifecycleState) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS


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
