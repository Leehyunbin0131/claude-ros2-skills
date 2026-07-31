#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

MAX_DETECTIONS = 20
POINT_CAMERA = (0.1, 0.05, 2.0)


class PointProjector(Node):

    def __init__(self):
        super().__init__('point_projector')
        self._camera_info = None
        self._detection_count = 0

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo,
            '/camera/camera_info',
            self._camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self._image_callback,
            qos_profile_sensor_data,
        )

    def _camera_info_callback(self, msg):
        self._camera_info = msg

    def _image_callback(self, msg):
        if self._camera_info is None or self._detection_count >= MAX_DETECTIONS:
            return

        k = self._camera_info.k
        fx, fy, cx, cy = k[0], k[4], k[2], k[5]

        x, y, z = POINT_CAMERA
        u = fx * (x / z) + cx
        v = fy * (y / z) + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 20.0
        detection.bbox.size_y = 20.0

        self._detection_pub.publish(detection)
        self._detection_count += 1


def main():
    rclpy.init()
    node = PointProjector()
    try:
        while rclpy.ok() and node._detection_count < MAX_DETECTIONS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
