#!/usr/bin/env python3
"""Broadcasts odom -> base_link at 20 Hz and looks up the same transform."""
import sys

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformBroadcaster, TransformException

RATE_HZ = 20.0
PERIOD_S = 1.0 / RATE_HZ
NUM_BROADCASTS = 20
X_VELOCITY = 0.05  # m/s


class OdomBaseLinkTfNode(Node):
    def __init__(self):
        super().__init__('odom_base_link_tf_node')
        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()
        self.count = 0
        self.timer = self.create_timer(PERIOD_S, self.timer_callback)

    def timer_callback(self):
        self.count += 1
        now = self.get_clock().now()
        x = X_VELOCITY * (self.count * PERIOD_S)

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

        # Publish the real /tf message ...
        self.broadcaster.sendTransform(t)
        # ... and feed our own buffer directly so the lookup below is
        # deterministic (no need to wait for the /tf subscription to
        # deliver the message back to this same process/callback).
        self.buffer.set_transform(t, 'default_authority')

        try:
            looked_up = self.buffer.lookup_transform('odom', 'base_link', now)
            t_sec = now.nanoseconds / 1e9
            self.get_logger().info(
                f'TF {t_sec:.3f} {looked_up.transform.translation.x:.3f}'
            )
        except TransformException as e:
            self.get_logger().error(f'TF lookup failed: {e}')

        if self.count >= NUM_BROADCASTS:
            future_time = now + Duration(seconds=5)
            try:
                self.buffer.lookup_transform('odom', 'base_link', future_time)
                self.get_logger().info('EXTRAP no exception raised')
            except TransformException as e:
                self.get_logger().info(f'EXTRAP {e}')

            self.timer.cancel()
            rclpy.shutdown()


def main():
    rclpy.init()
    node = OdomBaseLinkTfNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
