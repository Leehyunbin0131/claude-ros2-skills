#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField

MAX_CLOUDS = 20

# encoding -> (numpy dtype, scale to metres, treat-zero-as-invalid)
DEPTH_ENCODINGS = {
    '16UC1': (np.uint16, 0.001, True),
    'mono16': (np.uint16, 0.001, True),
    '32FC1': (np.float32, 1.0, False),
}


class DepthToPointCloud(Node):

    def __init__(self):
        super().__init__('depth_to_pointcloud')
        self.camera_info = None
        self.cloud_count = 0

        self.create_subscription(
            CameraInfo, '/depth/camera_info', self.camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/depth/image_raw', self.image_cb,
            qos_profile_sensor_data)
        self.pub = self.create_publisher(PointCloud2, '/points', 10)

    def camera_info_cb(self, msg):
        self.camera_info = msg

    def image_cb(self, msg):
        if self.camera_info is None:
            return

        depth = self.decode_depth(msg)
        if depth is None:
            return

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        height, width = depth.shape
        us, vs = np.meshgrid(np.arange(width), np.arange(height))

        valid = np.isfinite(depth) & (depth > 0.0)

        z = depth[valid]
        u = us[valid].astype(np.float32)
        v = vs[valid].astype(np.float32)

        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        points = np.empty((z.shape[0], 3), dtype=np.float32)
        points[:, 0] = x
        points[:, 1] = y
        points[:, 2] = z

        cloud_msg = self.build_cloud(msg.header, points)
        self.pub.publish(cloud_msg)
        self.cloud_count += 1
        self.get_logger().info(f'CLOUD {points.shape[0]}')

        if self.cloud_count >= MAX_CLOUDS:
            rclpy.shutdown()

    def decode_depth(self, msg):
        entry = DEPTH_ENCODINGS.get(msg.encoding)
        if entry is None:
            self.get_logger().warn(f'Unsupported depth encoding: {msg.encoding}')
            return None
        dtype, scale, zero_invalid = entry
        itemsize = np.dtype(dtype).itemsize

        raw = np.frombuffer(msg.data, dtype=dtype)
        stride = msg.step // itemsize
        raw = raw.reshape(msg.height, stride)[:, :msg.width]

        depth = raw.astype(np.float32) * scale
        if zero_invalid:
            depth[raw == 0] = np.nan
        else:
            depth[~np.isfinite(raw)] = np.nan
        return depth

    def build_cloud(self, header, points):
        msg = PointCloud2()
        msg.header = header
        msg.height = 1
        msg.width = points.shape[0]
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 12
        msg.row_step = msg.point_step * points.shape[0]
        msg.is_dense = True
        msg.data = points.tobytes()
        return msg


def main(args=None):
    rclpy.init(args=args)
    node = DepthToPointCloud()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
