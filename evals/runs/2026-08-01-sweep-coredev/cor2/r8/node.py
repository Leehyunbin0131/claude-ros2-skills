#!/usr/bin/env python3
import time

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformListener, TransformException


def main():
    rclpy.init()
    node = Node('odom_base_link_tf_node')

    broadcaster = TransformBroadcaster(node)
    tf_buffer = Buffer()
    tf_listener = TransformListener(tf_buffer, node)  # noqa: F841 (keeps subscription alive)

    rate_hz = 20.0
    period = 1.0 / rate_hz
    velocity = 0.05  # m/s
    max_count = 20

    start_time = node.get_clock().now()
    next_tick = time.monotonic()
    count = 0

    while rclpy.ok() and count < max_count:
        now = node.get_clock().now()
        elapsed = (now - start_time).nanoseconds / 1e9
        x = velocity * elapsed

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
        broadcaster.sendTransform(t)

        # Give the just-published transform a chance to loop back through
        # the /tf subscription before we try to look it up at the same stamp.
        wait_deadline = time.monotonic() + 0.5
        while time.monotonic() < wait_deadline:
            rclpy.spin_once(node, timeout_sec=0.01)
            if tf_buffer.can_transform('odom', 'base_link', now):
                break

        try:
            looked_up = tf_buffer.lookup_transform('odom', 'base_link', now)
            node.get_logger().info(
                f'TF {elapsed:.4f} {looked_up.transform.translation.x:.4f}'
            )
        except TransformException as e:
            node.get_logger().info(f'TF {elapsed:.4f} lookup_failed: {e}')

        count += 1
        next_tick += period
        sleep_time = next_tick - time.monotonic()
        if sleep_time > 0:
            time.sleep(sleep_time)

    future_time = node.get_clock().now() + Duration(seconds=5.0)
    try:
        tf_buffer.lookup_transform('odom', 'base_link', future_time)
        node.get_logger().info('EXTRAP no exception raised')
    except TransformException as e:
        node.get_logger().info(f'EXTRAP {e}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
