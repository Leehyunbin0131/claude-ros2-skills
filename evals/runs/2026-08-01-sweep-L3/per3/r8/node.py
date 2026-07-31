#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField

MAX_CLOUDS = 20


class DepthToPointCloud(Node):
    def __init__(self):
        super().__init__('depth_to_pointcloud')
        self.camera_info = None
        self.cloud_count = 0

        self.create_subscription(
            CameraInfo, '/depth/camera_info', self.camera_info_callback,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/depth/image_raw', self.image_callback,
            qos_profile_sensor_data)
        self.pub = self.create_publisher(PointCloud2, '/points', 10)

    def camera_info_callback(self, msg):
        self.camera_info = msg

    def image_callback(self, msg):
        if self.camera_info is None:
            return

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        if msg.encoding == '16UC1':
            depth = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
            depth = depth.astype(np.float32) / 1000.0
            valid = depth > 0
        elif msg.encoding == '32FC1':
            depth = np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, msg.width)
            valid = np.isfinite(depth) & (depth > 0)
        else:
            self.get_logger().warn(f'Unsupported depth encoding: {msg.encoding}')
            return

        us, vs = np.meshgrid(np.arange(msg.width), np.arange(msg.height))
        z = depth
        x = (us - cx) * z / fx
        y = (vs - cy) * z / fy

        points = np.stack([x[valid], y[valid], z[valid]], axis=-1).astype(np.float32)

        cloud_msg = self.make_cloud(msg.header, points)
        self.pub.publish(cloud_msg)

        n_points = points.shape[0]
        self.get_logger().info(f'CLOUD {n_points}')

        self.cloud_count += 1
        if self.cloud_count >= MAX_CLOUDS:
            sys.exit(0)

    @staticmethod
    def make_cloud(header, points):
        cloud = PointCloud2()
        cloud.header = header
        cloud.height = 1
        cloud.width = points.shape[0]
        cloud.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud.is_bigendian = False
        cloud.point_step = 12
        cloud.row_step = cloud.point_step * cloud.width
        cloud.is_dense = True
        cloud.data = points.tobytes()
        return cloud


def main(args=None):
    rclpy.init(args=args)
    node = DepthToPointCloud()
    exit_code = 0
    try:
        rclpy.spin(node)
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 0
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
