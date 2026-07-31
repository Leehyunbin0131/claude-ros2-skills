#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

POINT_CAMERA = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class ProjectorNode(Node):
    def __init__(self):
        super().__init__('projector_node')
        self._k = None
        self._count = 0

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._on_camera_info, qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self._on_image, qos_profile_sensor_data)
        self._pub = self.create_publisher(Detection2D, '/detection', 10)

    def _on_camera_info(self, msg: CameraInfo):
        self._k = msg.k

    def _on_image(self, msg: Image):
        if self._k is None:
            return
        if self._count >= MAX_DETECTIONS:
            return

        fx, _, cx = self._k[0], self._k[1], self._k[2]
        fy, cy = self._k[4], self._k[5]

        x, y, z = POINT_CAMERA
        u = fx * x / z + cx
        v = fy * y / z + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        det = Detection2D()
        det.header = msg.header
        det.bbox.center.position.x = u
        det.bbox.center.position.y = v
        det.bbox.center.theta = 0.0
        det.bbox.size_x = 0.0
        det.bbox.size_y = 0.0
        self._pub.publish(det)

        self._count += 1


def main():
    rclpy.init()
    node = ProjectorNode()
    try:
        while rclpy.ok() and node._count < MAX_DETECTIONS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
