#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import TransformStamped
from tf2_ros import (
    TransformBroadcaster,
    Buffer,
    TransformListener,
    LookupException,
    ConnectivityException,
    ExtrapolationException,
)

RATE_HZ = 20.0
PERIOD_S = 1.0 / RATE_HZ
X_VELOCITY = 0.05  # m/s
NUM_SAMPLES = 20


class TfDemoNode(Node):
    def __init__(self):
        super().__init__('tf_demo_node')
        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()
        # spin_thread=True lets the listener process incoming /tf messages
        # in the background while the main thread does blocking lookups.
        self.listener = TransformListener(self.buffer, self, spin_thread=True)


def broadcast(node: TfDemoNode, stamp, x: float) -> None:
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
    node.broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = TfDemoNode()

    start = node.get_clock().now()
    tf_count = 0

    try:
        next_tick = time.monotonic()
        while tf_count < NUM_SAMPLES:
            now = node.get_clock().now()
            elapsed = (now - start).nanoseconds * 1e-9
            x = X_VELOCITY * elapsed

            broadcast(node, now, x)

            try:
                looked_up = node.buffer.lookup_transform(
                    'odom', 'base_link', now, timeout=Duration(seconds=1.0)
                )
                lx = looked_up.transform.translation.x
                node.get_logger().info(f'TF {elapsed:.4f} {lx:.4f}')
                tf_count += 1
            except (LookupException, ConnectivityException, ExtrapolationException) as e:
                node.get_logger().warn(f'lookup failed, retrying: {e}')

            next_tick += PERIOD_S
            sleep_time = next_tick - time.monotonic()
            if sleep_time > 0:
                time.sleep(sleep_time)

        future_time = node.get_clock().now() + Duration(seconds=5.0)
        try:
            node.buffer.lookup_transform(
                'odom', 'base_link', future_time, timeout=Duration(seconds=0.0)
            )
            node.get_logger().info('EXTRAP no exception raised')
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            node.get_logger().info(f'EXTRAP {e}')

    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
