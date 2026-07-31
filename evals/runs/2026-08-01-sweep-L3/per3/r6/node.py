#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField
from std_msgs.msg import Header

MAX_CLOUDS = 20

# Depth encodings we know how to interpret, and how to get metres from them.
_ENCODING_SCALE = {
    '16UC1': 0.001,   # millimetres -> metres
    'mono16': 0.001,  # millimetres -> metres
    '32FC1': 1.0,     # already metres
}


class DepthToPointCloud(Node):

    def __init__(self):
        super().__init__('depth_to_pointcloud')

        self._camera_info = None
        self._cloud_count = 0

        self.create_subscription(
            CameraInfo, '/depth/camera_info', self._camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/depth/image_raw', self._image_cb,
            qos_profile_sensor_data)

        self._pub = self.create_publisher(
            PointCloud2, '/points', qos_profile_sensor_data)

    @property
    def cloud_count(self):
        return self._cloud_count

    def _camera_info_cb(self, msg):
        self._camera_info = msg

    def _image_cb(self, msg):
        if self._camera_info is None:
            return

        encoding = msg.encoding
        if encoding not in _ENCODING_SCALE:
            self.get_logger().warn(f'Unsupported depth encoding: {encoding}')
            return
        scale = _ENCODING_SCALE[encoding]

        endian = '>' if msg.is_bigendian else '<'
        if encoding in ('16UC1', 'mono16'):
            dtype = np.dtype(endian + 'u2')
        else:  # 32FC1
            dtype = np.dtype(endian + 'f4')

        raw = np.frombuffer(msg.data, dtype=dtype)
        row_elems = msg.step // dtype.itemsize
        raw = raw.reshape(msg.height, row_elems)[:, :msg.width]

        depth = raw.astype(np.float32) * scale

        fx = self._camera_info.k[0]
        fy = self._camera_info.k[4]
        cx = self._camera_info.k[2]
        cy = self._camera_info.k[5]

        if encoding in ('16UC1', 'mono16'):
            valid = raw != 0
        else:
            valid = np.isfinite(depth) & (depth > 0.0)

        v_idx, u_idx = np.nonzero(valid)
        z = depth[v_idx, u_idx]
        x = (u_idx.astype(np.float32) - cx) * z / fx
        y = (v_idx.astype(np.float32) - cy) * z / fy

        points = np.empty((z.shape[0], 3), dtype=np.float32)
        points[:, 0] = x
        points[:, 1] = y
        points[:, 2] = z

        cloud_msg = self._make_cloud(points, msg.header)
        self._pub.publish(cloud_msg)

        self._cloud_count += 1
        self.get_logger().info(f'CLOUD {points.shape[0]}')

    @staticmethod
    def _make_cloud(points, header: Header) -> PointCloud2:
        n = points.shape[0]
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        point_step = 12
        cloud = PointCloud2()
        cloud.header = header
        cloud.height = 1
        cloud.width = n
        cloud.fields = fields
        cloud.is_bigendian = False
        cloud.point_step = point_step
        cloud.row_step = point_step * n
        cloud.is_dense = True
        cloud.data = points.tobytes()
        return cloud


def main():
    rclpy.init()
    node = DepthToPointCloud()
    try:
        while rclpy.ok() and node.cloud_count < MAX_CLOUDS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
