#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image, PointCloud2
from sensor_msgs_py import point_cloud2

TARGET_CLOUDS = 20

# encoding -> (numpy dtype, metres-per-unit scale)
DEPTH_ENCODINGS = {
    '16UC1': (np.uint16, 0.001),
    'mono16': (np.uint16, 0.001),
    '32FC1': (np.float32, 1.0),
}


class DepthToPointCloud(Node):

    def __init__(self):
        super().__init__('depth_to_pointcloud')
        self.camera_info = None
        self.clouds_published = 0

        self.create_subscription(
            CameraInfo, '/depth/camera_info', self.camera_info_cb, 10)
        self.create_subscription(
            Image, '/depth/image_raw', self.image_cb, 10)
        self.cloud_pub = self.create_publisher(PointCloud2, '/points', 10)

    def camera_info_cb(self, msg):
        self.camera_info = msg

    def image_cb(self, msg):
        if self.camera_info is None:
            return

        if msg.encoding not in DEPTH_ENCODINGS:
            self.get_logger().error(f'Unsupported depth encoding: {msg.encoding}')
            return

        dtype, scale = DEPTH_ENCODINGS[msg.encoding]
        dtype = np.dtype(dtype).newbyteorder('>' if msg.is_bigendian else '<')
        itemsize = dtype.itemsize

        raw = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
        depth = raw[:, :msg.width * itemsize].view(dtype).reshape(msg.height, msg.width)
        depth_m = depth.astype(np.float32) * np.float32(scale)

        if np.issubdtype(dtype, np.integer):
            valid = depth != 0
        else:
            valid = np.isfinite(depth_m) & (depth_m > 0.0)

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        us, vs = np.meshgrid(np.arange(msg.width), np.arange(msg.height))

        z = depth_m[valid]
        x = (us[valid].astype(np.float32) - np.float32(cx)) * z / np.float32(fx)
        y = (vs[valid].astype(np.float32) - np.float32(cy)) * z / np.float32(fy)

        points = np.stack([x, y, z], axis=-1).astype(np.float32)

        cloud_msg = point_cloud2.create_cloud_xyz32(msg.header, points)
        self.cloud_pub.publish(cloud_msg)

        n_points = points.shape[0]
        self.get_logger().info(f'CLOUD {n_points}')

        self.clouds_published += 1
        if self.clouds_published >= TARGET_CLOUDS:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = DepthToPointCloud()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
