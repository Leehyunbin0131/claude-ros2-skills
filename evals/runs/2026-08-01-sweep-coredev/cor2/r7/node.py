#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformException


class OdomBaseLinkTfNode(Node):
    def __init__(self):
        super().__init__('odom_base_link_tf_node')

        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()

        self.rate_hz = 20.0
        self.velocity_x = 0.05  # m/s
        self.max_count = 20
        self.count = 0
        self.extrap_done = False

        self.start_time = self.get_clock().now()
        self.timer = self.create_timer(1.0 / self.rate_hz, self.on_timer)

    def on_timer(self):
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        x = self.velocity_x * elapsed

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

        # Broadcast on the wire.
        self.broadcaster.sendTransform(t)
        # Feed our own buffer directly so the lookup below is deterministic
        # rather than racing against this node's own /tf subscription.
        self.buffer.set_transform(t, 'default_authority')

        try:
            looked_up = self.buffer.lookup_transform('odom', 'base_link', now)
            lx = looked_up.transform.translation.x
            self.get_logger().info(f'TF {now.nanoseconds / 1e9:.3f} {lx:.3f}')
        except TransformException as ex:
            self.get_logger().info(f'TF lookup failed: {ex}')

        self.count += 1

        if self.count == self.max_count and not self.extrap_done:
            self.extrap_done = True
            future_time = now + Duration(seconds=5.0)
            try:
                self.buffer.lookup_transform('odom', 'base_link', future_time)
                self.get_logger().info('EXTRAP no exception raised')
            except TransformException as ex:
                self.get_logger().info(f'EXTRAP {ex}')

        if self.count >= self.max_count and self.extrap_done:
            self.timer.cancel()
            rclpy.shutdown()


def main():
    rclpy.init()
    node = OdomBaseLinkTfNode()
    try:
        rclpy.spin(node)
    finally:
        if rclpy.ok():
            node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
