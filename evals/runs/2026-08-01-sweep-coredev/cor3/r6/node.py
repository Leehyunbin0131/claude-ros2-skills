#!/usr/bin/env python3
import rclpy
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Int32


class CounterNode(LifecycleNode):

    def __init__(self):
        super().__init__('counter')
        self._count = 0
        self._publisher = None
        self._active = False
        # Timer runs for the whole node lifetime; the active flag (and the
        # publisher only existing once configured) gate actual publishing.
        self._timer = self.create_timer(0.1, self._tick)
        self.get_logger().info('STATE unconfigured')

    def _tick(self):
        if not self._active or self._publisher is None:
            return
        msg = Int32()
        msg.data = self._count
        self._count += 1
        self._publisher.publish(msg)

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._publisher = self.create_publisher(Int32, '/count', 10)
        self.get_logger().info('STATE inactive')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        result = super().on_activate(state)
        self._active = True
        self.get_logger().info('STATE active')
        return result

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = False
        result = super().on_deactivate(state)
        self.get_logger().info('STATE inactive')
        return result

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = False
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE unconfigured')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = False
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        self.get_logger().info('STATE finalized')
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = False
        self.get_logger().info('STATE errorprocessing')
        return TransitionCallbackReturn.SUCCESS


def main():
    rclpy.init()
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
