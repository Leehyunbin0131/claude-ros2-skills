#!/usr/bin/env python3
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import message_filters
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField

MAX_CLOUDS = 20


class DepthToPointCloud(Node):
    def __init__(self):
        super().__init__('depth_to_pointcloud')

        self.publisher = self.create_publisher(PointCloud2, '/points', 10)

        image_sub = message_filters.Subscriber(
            self, Image, '/depth/image_raw', qos_profile=qos_profile_sensor_data
        )
        info_sub = message_filters.Subscriber(
            self, CameraInfo, '/depth/camera_info', qos_profile=qos_profile_sensor_data
        )
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [image_sub, info_sub], queue_size=10, slop=0.1
        )
        self.sync.registerCallback(self.callback)

        self.cloud_count = 0

    def decode_depth(self, image_msg: Image) -> np.ndarray:
        encoding = image_msg.encoding
        if encoding == '16UC1' or encoding == 'mono16':
            dtype = np.dtype(np.uint16)
        elif encoding == '32FC1':
            dtype = np.dtype(np.float32)
        else:
            raise ValueError(f'Unsupported depth encoding: {encoding}')

        if image_msg.is_bigendian:
            dtype = dtype.newbyteorder('>')

        raw = np.frombuffer(image_msg.data, dtype=dtype)
        stride = image_msg.step // dtype.itemsize
        raw = raw.reshape(image_msg.height, stride)[:, :image_msg.width]

        if dtype.kind == 'u':
            depth_m = raw.astype(np.float32) / 1000.0
            valid = raw != 0
        else:
            depth_m = raw.astype(np.float32)
            valid = np.isfinite(depth_m) & (depth_m > 0.0)

        return depth_m, valid

    def callback(self, image_msg: Image, info_msg: CameraInfo):
        try:
            depth_m, valid = self.decode_depth(image_msg)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        fx = info_msg.k[0]
        fy = info_msg.k[4]
        cx = info_msg.k[2]
        cy = info_msg.k[5]

        height, width = depth_m.shape
        us, vs = np.meshgrid(np.arange(width), np.arange(height))

        z = depth_m[valid]
        u = us[valid]
        v = vs[valid]
        x = (u.astype(np.float32) - cx) * z / fx
        y = (v.astype(np.float32) - cy) * z / fy

        n_points = z.shape[0]

        points = np.zeros(n_points, dtype=[('x', np.float32), ('y', np.float32), ('z', np.float32)])
        points['x'] = x
        points['y'] = y
        points['z'] = z

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
        cloud_msg.data = points.tobytes()
        cloud_msg.is_dense = True

        self.publisher.publish(cloud_msg)
        self.get_logger().info(f'CLOUD {n_points}')

        self.cloud_count += 1
        if self.cloud_count >= MAX_CLOUDS:
            self.get_logger().info(f'Published {MAX_CLOUDS} clouds, shutting down')
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = DepthToPointCloud()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
