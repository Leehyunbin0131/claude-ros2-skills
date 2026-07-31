#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from vision_msgs.msg import BoundingBox2D, Detection2D, Point2D, Pose2D

POINT_3D = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class PointProjector(Node):
    def __init__(self):
        super().__init__('point_projector')
        self._camera_info = None
        self._count = 0

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)
        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self._image_cb,
            qos_profile_sensor_data)

    def _camera_info_cb(self, msg):
        self._camera_info = msg

    def _image_cb(self, msg):
        if self._camera_info is None:
            return

        k = self._camera_info.k
        fx, cx = k[0], k[2]
        fy, cy = k[4], k[5]

        x, y, z = POINT_3D
        u = fx * x / z + cx
        v = fy * y / z + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header
        detection.bbox = BoundingBox2D()
        detection.bbox.center = Pose2D()
        detection.bbox.center.position = Point2D()
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 1.0
        detection.bbox.size_y = 1.0

        self._detection_pub.publish(detection)
        self._count += 1

    @property
    def count(self):
        return self._count


def main():
    rclpy.init()
    node = PointProjector()

    try:
        while rclpy.ok() and node.count < MAX_DETECTIONS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
