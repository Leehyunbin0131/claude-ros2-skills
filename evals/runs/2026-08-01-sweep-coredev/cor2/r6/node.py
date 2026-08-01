#!/usr/bin/env python3
"""Broadcast a dynamic odom->base_link TF at 20 Hz and look each one back up."""
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformListener, TransformException

RATE_HZ = 20.0
X_VEL = 0.05
NUM_SAMPLES = 20
LOOKUP_TIMEOUT = Duration(seconds=0.5)
EXTRAP_AHEAD = Duration(seconds=5.0)


class TfNode(Node):

    def __init__(self):
        super().__init__('tf_broadcast_lookup_node')
        self.broadcaster = TransformBroadcaster(self)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.start_time = self.get_clock().now()
        self.count = 0
        self.done = False

        self.timer = self.create_timer(1.0 / RATE_HZ, self.on_timer)

    def on_timer(self):
        if self.count >= NUM_SAMPLES:
            return

        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        x = X_VEL * elapsed

        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = x
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0
        self.broadcaster.sendTransform(t)

        try:
            looked_up = self.tf_buffer.lookup_transform(
                'odom', 'base_link', now, timeout=LOOKUP_TIMEOUT)
            self.get_logger().info(
                f'TF {elapsed:.3f} {looked_up.transform.translation.x:.3f}')
        except TransformException as ex:
            self.get_logger().info(f'TF {elapsed:.3f} ERROR {ex}')

        self.count += 1

        if self.count == NUM_SAMPLES:
            future_time = now + EXTRAP_AHEAD
            try:
                self.tf_buffer.lookup_transform('odom', 'base_link', future_time)
                self.get_logger().info('EXTRAP no exception raised')
            except TransformException as ex:
                self.get_logger().info(f'EXTRAP {ex}')
            self.done = True


def main():
    rclpy.init()
    node = TfNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        while rclpy.ok() and not node.done:
            executor.spin_once(timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
