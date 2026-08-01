#!/usr/bin/env python3
"""ROS 2 Jazzy node: broadcasts odom -> base_link and looks up each broadcast."""
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformListener, TransformException


class OdomBaseLinkNode(Node):
    def __init__(self):
        super().__init__('odom_base_link_node')

        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

        self.rate_hz = 20.0
        self.period = 1.0 / self.rate_hz
        self.start_time = self.get_clock().now()

        self.max_tf_logs = 20
        self.tf_log_count = 0
        self.pending = None  # (stamp: Time, elapsed: float, x: float)
        self.extrap_done = False

        self.timer = self.create_timer(self.period, self.timer_callback)

    def timer_callback(self):
        if self.extrap_done:
            return

        # Try to resolve the previously broadcast transform first, giving the
        # (asynchronous) tf listener a chance to have received it by now.
        if self.pending is not None:
            stamp, elapsed, x = self.pending
            try:
                self.buffer.lookup_transform('odom', 'base_link', stamp)
                print(f'TF {elapsed:.3f} {x:.3f}', flush=True)
                self.tf_log_count += 1
                self.pending = None
            except TransformException:
                pass  # not yet available in the buffer, retry next cycle

        if self.tf_log_count >= self.max_tf_logs:
            self.do_extrapolation_lookup()
            return

        # Broadcast the current transform.
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
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
        self.broadcaster.sendTransform(t)

        if self.pending is None:
            self.pending = (now, elapsed, x)

    def do_extrapolation_lookup(self):
        future_time = self.get_clock().now() + Duration(seconds=5.0)
        try:
            self.buffer.lookup_transform('odom', 'base_link', future_time)
            print('EXTRAP no exception raised', flush=True)
        except TransformException as ex:
            print(f'EXTRAP {ex}', flush=True)
        self.extrap_done = True


def main():
    rclpy.init()
    node = OdomBaseLinkNode()
    try:
        while rclpy.ok() and not node.extrap_done:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
