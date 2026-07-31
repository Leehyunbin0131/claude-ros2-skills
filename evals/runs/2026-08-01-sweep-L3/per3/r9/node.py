#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField

MAX_CLOUDS = 20


class DepthToPointCloud(Node):
    def __init__(self):
        super().__init__('depth_to_pointcloud')

        self.camera_info = None
        self.cloud_count = 0

        self.cloud_pub = self.create_publisher(PointCloud2, '/points', 10)

        self.info_sub = self.create_subscription(
            CameraInfo,
            '/depth/camera_info',
            self.camera_info_callback,
            qos_profile_sensor_data,
        )
        self.image_sub = self.create_subscription(
            Image,
            '/depth/image_raw',
            self.image_callback,
            qos_profile_sensor_data,
        )

    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def image_callback(self, msg: Image):
        if self.camera_info is None:
            return

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        depth_m, valid = self._decode_depth(msg)
        if depth_m is None:
            self.get_logger().warn(f'Unsupported depth encoding: {msg.encoding}')
            return

        height, width = depth_m.shape

        us, vs = np.meshgrid(np.arange(width), np.arange(height))

        us = us[valid].astype(np.float32)
        vs = vs[valid].astype(np.float32)
        zs = depth_m[valid].astype(np.float32)

        xs = (us - cx) * zs / fx
        ys = (vs - cy) * zs / fy

        points = np.column_stack((xs, ys, zs)).astype(np.float32)

        cloud_msg = self._make_pointcloud2(msg.header, points)
        self.cloud_pub.publish(cloud_msg)

        n_points = points.shape[0]
        self.get_logger().info(f'CLOUD {n_points}')

        self.cloud_count += 1
        if self.cloud_count >= MAX_CLOUDS:
            rclpy.shutdown()

    def _decode_depth(self, msg: Image):
        height = msg.height
        width = msg.width

        if msg.encoding == '16UC1' or msg.encoding == 'mono16':
            dtype = np.uint16
            raw = np.frombuffer(msg.data, dtype=dtype)
            raw = raw.reshape(height, msg.step // np.dtype(dtype).itemsize)[:, :width]
            depth_m = raw.astype(np.float32) / 1000.0
            valid = raw != 0
        elif msg.encoding == '32FC1':
            dtype = np.float32
            raw = np.frombuffer(msg.data, dtype=dtype)
            raw = raw.reshape(height, msg.step // np.dtype(dtype).itemsize)[:, :width]
            depth_m = raw.astype(np.float32)
            valid = np.isfinite(depth_m) & (depth_m > 0.0)
        else:
            return None, None

        valid = valid & np.isfinite(depth_m) & (depth_m > 0.0)
        return depth_m, valid

    def _make_pointcloud2(self, header, points: np.ndarray) -> PointCloud2:
        cloud = PointCloud2()
        cloud.header = header

        cloud.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud.is_bigendian = False
        cloud.point_step = 12
        cloud.height = 1
        cloud.width = points.shape[0]
        cloud.row_step = cloud.point_step * cloud.width
        cloud.is_dense = True
        cloud.data = points.astype(np.float32).tobytes()

        return cloud


def main():
    rclpy.init()
    node = DepthToPointCloud()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
