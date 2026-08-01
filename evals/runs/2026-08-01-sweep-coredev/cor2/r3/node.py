#!/usr/bin/env python3
"""Broadcast a dynamic odom -> base_link transform at 20 Hz and look it up."""

import time

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from tf2_ros import TransformBroadcaster, TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from geometry_msgs.msg import TransformStamped

RATE_HZ = 20.0
PERIOD_S = 1.0 / RATE_HZ
X_VELOCITY = 0.05  # m/s
NUM_SAMPLES = 20
LOOKUP_RETRY_TIMEOUT_S = 5.0


class OdomBaseLinkTfNode(Node):

    def __init__(self):
        super().__init__('odom_base_link_tf_node')
        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self, spin_thread=False)
        self.start_time = self.get_clock().now()

    def broadcast(self):
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        x = X_VELOCITY * elapsed

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
        return now

    def lookup_with_retry(self, target_time, timeout_s):
        deadline = time.monotonic() + timeout_s
        last_exc = None
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.01)
            try:
                return self.buffer.lookup_transform('odom', 'base_link', target_time)
            except TransformException as exc:
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        raise RuntimeError('lookup_with_retry timed out with no exception recorded')


def main():
    rclpy.init()
    node = OdomBaseLinkTfNode()
    try:
        for _ in range(NUM_SAMPLES):
            loop_start = time.monotonic()

            stamp = node.broadcast()
            transform = node.lookup_with_retry(stamp, LOOKUP_RETRY_TIMEOUT_S)

            t_sec = stamp.nanoseconds / 1e9
            x = transform.transform.translation.x
            node.get_logger().info(f'TF {t_sec:.6f} {x:.6f}')

            sleep_time = PERIOD_S - (time.monotonic() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        future_time = node.get_clock().now() + Duration(seconds=5)
        try:
            node.buffer.lookup_transform('odom', 'base_link', future_time)
        except TransformException as exc:
            node.get_logger().info(f'EXTRAP {exc}')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
