#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import message_filters
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Header

MAX_CLOUDS = 20

FIELDS = [
    PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
]


class DepthToPointCloud(Node):

    def __init__(self):
        super().__init__('depth_to_pointcloud')

        self._cloud_count = 0

        self._pub = self.create_publisher(PointCloud2, '/points', 10)

        self._image_sub = message_filters.Subscriber(
            self, Image, '/depth/image_raw', qos_profile=qos_profile_sensor_data)
        self._info_sub = message_filters.Subscriber(
            self, CameraInfo, '/depth/camera_info', qos_profile=qos_profile_sensor_data)

        self._sync = message_filters.ApproximateTimeSynchronizer(
            [self._image_sub, self._info_sub], queue_size=10, slop=0.1)
        self._sync.registerCallback(self._on_depth)

    def _decode_depth(self, msg: Image) -> np.ndarray:
        h, w = msg.height, msg.width
        step = msg.step

        if msg.encoding == '16UC1' or msg.encoding == 'mono16':
            itemsize = 2
            dtype = np.uint16
            raw = np.frombuffer(msg.data, dtype=dtype)
            row_elems = step // itemsize
            arr = raw.reshape(h, row_elems)[:, :w]
            depth_m = arr.astype(np.float32) / 1000.0
            invalid = arr == 0
        elif msg.encoding == '32FC1':
            itemsize = 4
            dtype = np.float32
            raw = np.frombuffer(msg.data, dtype=dtype)
            row_elems = step // itemsize
            arr = raw.reshape(h, row_elems)[:, :w]
            depth_m = arr.astype(np.float32)
            invalid = ~np.isfinite(arr) | (arr <= 0.0)
        else:
            raise ValueError(f'Unsupported depth encoding: {msg.encoding}')

        depth_m[invalid] = np.nan
        return depth_m

    def _on_depth(self, image_msg: Image, info_msg: CameraInfo):
        depth = self._decode_depth(image_msg)
        h, w = depth.shape

        k = info_msg.k
        fx, fy = k[0], k[4]
        cx, cy = k[2], k[5]

        us, vs = np.meshgrid(np.arange(w, dtype=np.float32),
                              np.arange(h, dtype=np.float32))

        valid = np.isfinite(depth)

        z = depth[valid]
        x = (us[valid] - cx) * z / fx
        y = (vs[valid] - cy) * z / fy

        points = np.column_stack((x, y, z)).astype(np.float32)

        header = Header()
        header.stamp = image_msg.header.stamp
        header.frame_id = image_msg.header.frame_id

        cloud_msg = pc2.create_cloud(header, FIELDS, points)
        self._pub.publish(cloud_msg)

        n_points = points.shape[0]
        self.get_logger().info(f'CLOUD {n_points}')

        self._cloud_count += 1
        if self._cloud_count >= MAX_CLOUDS:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = DepthToPointCloud()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()

    sys.exit(0)


if __name__ == '__main__':
    main()
