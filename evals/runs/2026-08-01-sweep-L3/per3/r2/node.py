#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, PointCloud2
from sensor_msgs_py import point_cloud2

MAX_CLOUDS = 20

ENCODING_DTYPES = {
    '16UC1': np.uint16,
    'mono16': np.uint16,
    '32FC1': np.float32,
}


class DepthToCloud(Node):
    def __init__(self):
        super().__init__('depth_to_cloud')
        self.camera_info = None
        self.count = 0

        self.create_subscription(
            CameraInfo, '/depth/camera_info', self._camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/depth/image_raw', self._depth_cb,
            qos_profile_sensor_data)
        self.pub = self.create_publisher(PointCloud2, '/points', 10)

    def _camera_info_cb(self, msg: CameraInfo):
        self.camera_info = msg

    def _depth_cb(self, msg: Image):
        if self.camera_info is None:
            return

        dtype = ENCODING_DTYPES.get(msg.encoding)
        if dtype is None:
            self.get_logger().warn(f'Unsupported depth encoding: {msg.encoding}')
            return

        itemsize = np.dtype(dtype).itemsize
        raw = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
        row_bytes = msg.width * itemsize
        depth_raw = raw[:, :row_bytes].view(dtype).reshape(msg.height, msg.width)

        if dtype == np.uint16:
            depth_m = depth_raw.astype(np.float32) / 1000.0
            valid = depth_raw != 0
        else:
            depth_m = depth_raw.astype(np.float32)
            valid = np.isfinite(depth_m) & (depth_m > 0.0)

        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        v, u = np.nonzero(valid)
        z = depth_m[v, u]
        x = (u.astype(np.float32) - cx) * z / fx
        y = (v.astype(np.float32) - cy) * z / fy

        points = np.stack((x, y, z), axis=-1).astype(np.float32)

        header = msg.header
        cloud_msg = point_cloud2.create_cloud_xyz32(header, points)
        self.pub.publish(cloud_msg)

        self.count += 1
        self.get_logger().info(f'CLOUD {points.shape[0]}')


def main():
    rclpy.init()
    node = DepthToCloud()
    try:
        while rclpy.ok() and node.count < MAX_CLOUDS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
