#!/usr/bin/env python3
import sys

import numpy as np
import message_filters
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField

MAX_CLOUDS = 20


class DepthToCloud(Node):
    def __init__(self):
        super().__init__('depth_to_cloud')
        self.count = 0
        self.pub = self.create_publisher(PointCloud2, '/points', 10)

        image_sub = message_filters.Subscriber(self, Image, '/depth/image_raw')
        info_sub = message_filters.Subscriber(self, CameraInfo, '/depth/camera_info')
        self.ts = message_filters.ApproximateTimeSynchronizer(
            [image_sub, info_sub], queue_size=10, slop=0.1)
        self.ts.registerCallback(self.on_frame)

    def on_frame(self, depth_msg: Image, info_msg: CameraInfo):
        points = self.depth_to_points(depth_msg, info_msg)

        cloud_msg = PointCloud2()
        cloud_msg.header = depth_msg.header
        cloud_msg.height = 1
        cloud_msg.width = points.shape[0]
        cloud_msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud_msg.is_bigendian = False
        cloud_msg.point_step = 12
        cloud_msg.row_step = 12 * points.shape[0]
        cloud_msg.is_dense = True
        cloud_msg.data = points.astype('<f4').tobytes()

        self.pub.publish(cloud_msg)
        self.count += 1
        self.get_logger().info(f'CLOUD {points.shape[0]}')

    def depth_to_points(self, depth_msg: Image, info_msg: CameraInfo) -> np.ndarray:
        height = depth_msg.height
        width = depth_msg.width
        encoding = depth_msg.encoding

        if encoding in ('16UC1', 'mono16'):
            dtype = np.uint16
        elif encoding == '32FC1':
            dtype = np.float32
        else:
            raise ValueError(f'Unsupported depth encoding: {encoding}')

        itemsize = np.dtype(dtype).itemsize
        row_bytes = width * itemsize
        raw = np.frombuffer(depth_msg.data, dtype=np.uint8).reshape(height, depth_msg.step)
        data = raw[:, :row_bytes].view(dtype).reshape(height, width)

        if dtype == np.uint16:
            depth = data.astype(np.float32) / 1000.0
            valid = data != 0
        else:
            depth = data
            valid = np.isfinite(depth) & (depth > 0.0)

        fx = info_msg.k[0]
        fy = info_msg.k[4]
        cx = info_msg.k[2]
        cy = info_msg.k[5]

        us, vs = np.meshgrid(np.arange(width, dtype=np.float32),
                              np.arange(height, dtype=np.float32))

        z = depth[valid]
        u = us[valid]
        v = vs[valid]

        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        return np.stack([x, y, z], axis=-1).astype(np.float32)


def main():
    rclpy.init()
    node = DepthToCloud()
    try:
        while rclpy.ok() and node.count < MAX_CLOUDS:
            rclpy.spin_once(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
