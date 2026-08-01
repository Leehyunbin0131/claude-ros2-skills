#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformBroadcaster, TransformException


class OdomBaseLinkTfNode(Node):

    def __init__(self):
        super().__init__('odom_base_link_tf_node')
        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()
        self.start_time = self.get_clock().now()

    def broadcast_and_lookup(self):
        stamp = self.get_clock().now()
        elapsed = (stamp - self.start_time).nanoseconds / 1e9
        x = 0.05 * elapsed

        t = TransformStamped()
        t.header.stamp = stamp.to_msg()
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
        # Populate the local buffer directly with the transform we just
        # broadcast so the lookup below is synchronous with the broadcast
        # (not dependent on /tf topic round-trip timing).
        self.buffer.set_transform(t, 'odom_base_link_tf_node')

        result = self.buffer.lookup_transform('odom', 'base_link', stamp)
        self.get_logger().info(
            f'TF {elapsed:.3f} {result.transform.translation.x:.4f}')

    def attempt_future_lookup(self):
        future_time = self.get_clock().now() + Duration(seconds=5.0)
        try:
            self.buffer.lookup_transform('odom', 'base_link', future_time)
            self.get_logger().info('EXTRAP no exception was raised')
        except TransformException as ex:
            self.get_logger().info(f'EXTRAP {ex}')


def main():
    rclpy.init()
    node = OdomBaseLinkTfNode()
    period = 1.0 / 20.0

    try:
        for _ in range(20):
            loop_start = time.monotonic()
            node.broadcast_and_lookup()
            elapsed = time.monotonic() - loop_start
            remaining = period - elapsed
            if remaining > 0.0:
                time.sleep(remaining)

        node.attempt_future_lookup()
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
