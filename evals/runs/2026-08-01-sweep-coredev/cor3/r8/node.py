#!/usr/bin/env python3
import rclpy
import rclpy.executors
from rclpy.lifecycle import Node as LifecycleNode
from rclpy.lifecycle import State, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._count = 0
        self._pub = None
        self._timer = None
        self.get_logger().info('STATE unconfigured')

    def _tick(self):
        msg = Int32()
        msg.data = self._count
        self._count += 1
        self._pub.publish(msg)

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self._pub = self.create_lifecycle_publisher(Int32, 'count', 10)
        self._timer = self.create_timer(0.1, self._tick)
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
        return TransitionCallbackReturn.SUCCESS


def main():
    rclpy.init()
    executor = rclpy.executors.MultiThreadedExecutor()
    node = CounterNode()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        executor.remove_node(node)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
