#!/usr/bin/env python3
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformListener, TransformException


class OdomBaseLinkNode(Node):
    def __init__(self):
        super().__init__('odom_base_link_node')
        self.broadcaster = TransformBroadcaster(self)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)


def main():
    rclpy.init()
    node = OdomBaseLinkNode()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    rate_hz = 20.0
    period = 1.0 / rate_hz
    start_time = node.get_clock().now()

    tf_count = 0
    try:
        while tf_count < 20:
            loop_start = time.time()

            now = node.get_clock().now()
            elapsed = (now - start_time).nanoseconds / 1e9
            x = 0.05 * elapsed

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

            node.broadcaster.sendTransform(t)

            try:
                looked_up = node.tf_buffer.lookup_transform(
                    'odom', 'base_link', now, timeout=Duration(seconds=1.0))
                lx = looked_up.transform.translation.x
                node.get_logger().info(f'TF {elapsed:.3f} {lx:.3f}')
            except TransformException as e:
                node.get_logger().info(f'TF {elapsed:.3f} lookup_failed: {e}')

            tf_count += 1

            sleep_time = period - (time.time() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        future_time = node.get_clock().now() + Duration(seconds=5.0)
        try:
            node.tf_buffer.lookup_transform(
                'odom', 'base_link', future_time, timeout=Duration(seconds=1.0))
            node.get_logger().info('EXTRAP no exception raised')
        except TransformException as e:
            node.get_logger().info(f'EXTRAP {e}')

    finally:
        rclpy.shutdown()
        spin_thread.join(timeout=2.0)

    sys.exit(0)


if __name__ == '__main__':
    main()
