#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration

from tf2_ros import TransformBroadcaster, Buffer, TransformException
from geometry_msgs.msg import TransformStamped

RATE_HZ = 20.0
PERIOD = 1.0 / RATE_HZ
VELOCITY_X = 0.05  # m/s
NUM_SAMPLES = 20
FUTURE_OFFSET_SEC = 5.0


class OdomBaseLinkTfNode(Node):
    def __init__(self):
        super().__init__('odom_base_link_tf_node')
        self.broadcaster = TransformBroadcaster(self)
        self.buffer = Buffer()

    def make_transform(self, stamp, x):
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
        return t

    def run(self):
        start_time = self.get_clock().now()
        last_stamp = start_time

        for _ in range(NUM_SAMPLES):
            loop_start = time.perf_counter()

            now = self.get_clock().now()
            elapsed = (now - start_time).nanoseconds * 1e-9
            x = VELOCITY_X * elapsed

            transform = self.make_transform(now, x)

            # Broadcast on /tf for real subscribers.
            self.broadcaster.sendTransform(transform)
            # Feed our own buffer directly so the lookup below is
            # guaranteed to have the data for this exact timestamp,
            # regardless of pub/sub scheduling.
            self.buffer.set_transform(transform, 'odom_base_link_tf_node')

            last_stamp = now

            try:
                looked_up = self.buffer.lookup_transform(
                    'odom', 'base_link', now)
                t_sec = now.nanoseconds * 1e-9
                self.get_logger().info(
                    f'TF {t_sec:.4f} {looked_up.transform.translation.x:.4f}')
            except TransformException as e:
                self.get_logger().info(f'EXTRAP {str(e)}')

            sleep_time = PERIOD - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        future_time = last_stamp + Duration(seconds=FUTURE_OFFSET_SEC)
        try:
            self.buffer.lookup_transform('odom', 'base_link', future_time)
            self.get_logger().info('EXTRAP no exception raised')
        except TransformException as e:
            self.get_logger().info(f'EXTRAP {str(e)}')


def main():
    rclpy.init(args=sys.argv)
    node = OdomBaseLinkTfNode()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
