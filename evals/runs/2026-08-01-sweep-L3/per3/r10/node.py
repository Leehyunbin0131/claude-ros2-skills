#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import message_filters
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField

MAX_CLOUDS = 20


def decode_depth(msg: Image) -> np.ndarray:
    """Return depth image as float32 metres, invalid pixels set to NaN."""
    if msg.encoding in ('16UC1', 'mono16'):
        dtype = np.uint16
        scale = 0.001
    elif msg.encoding == '32FC1':
        dtype = np.float32
        scale = 1.0
    else:
        raise ValueError(f'Unsupported depth encoding: {msg.encoding}')

    itemsize = np.dtype(dtype).itemsize
    raw = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    raw = raw[:, :msg.width * itemsize].copy()
    arr = raw.view(dtype).reshape(msg.height, msg.width)

    depth = arr.astype(np.float32) * scale
    if dtype == np.uint16:
        invalid = (arr == 0)
    else:
        invalid = ~np.isfinite(depth) | (depth <= 0.0)
    depth[invalid] = np.nan
    return depth


class DepthToPointCloud(Node):

    def __init__(self):
        super().__init__('depth_to_pointcloud')

        self.cloud_pub = self.create_publisher(PointCloud2, '/points', 10)

        image_sub = message_filters.Subscriber(
            self, Image, '/depth/image_raw', qos_profile=qos_profile_sensor_data)
        info_sub = message_filters.Subscriber(
            self, CameraInfo, '/depth/camera_info', qos_profile=qos_profile_sensor_data)

        self.sync = message_filters.ApproximateTimeSynchronizer(
            [image_sub, info_sub], queue_size=10, slop=0.1)
        self.sync.registerCallback(self.callback)

        self.cloud_count = 0

    def callback(self, image_msg: Image, info_msg: CameraInfo):
        try:
            depth = decode_depth(image_msg)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        fx = info_msg.k[0]
        fy = info_msg.k[4]
        cx = info_msg.k[2]
        cy = info_msg.k[5]

        height, width = depth.shape
        u, v = np.meshgrid(np.arange(width), np.arange(height))

        z = depth
        x = (u.astype(np.float32) - cx) * z / fx
        y = (v.astype(np.float32) - cy) * z / fy

        mask = np.isfinite(z)
        points = np.stack([x[mask], y[mask], z[mask]], axis=-1).astype(np.float32)
        n_points = points.shape[0]

        cloud_msg = PointCloud2()
        cloud_msg.header = image_msg.header
        cloud_msg.height = 1
        cloud_msg.width = n_points
        cloud_msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud_msg.is_bigendian = False
        cloud_msg.point_step = 12
        cloud_msg.row_step = 12 * n_points
        cloud_msg.is_dense = True
        cloud_msg.data = points.tobytes()

        self.cloud_pub.publish(cloud_msg)
        self.get_logger().info(f'CLOUD {n_points}')

        self.cloud_count += 1
        if self.cloud_count >= MAX_CLOUDS:
            rclpy.shutdown()


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
