#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

POINT_CAM = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20
BOX_SIZE_PX = 20.0


class PointProjectorNode(Node):
    def __init__(self):
        super().__init__('point_projector_node')
        self._camera_info = None
        self._detections_published = 0

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self._image_cb,
            qos_profile_sensor_data)

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)

    def _camera_info_cb(self, msg):
        self._camera_info = msg

    def _image_cb(self, msg):
        if self._camera_info is None:
            return
        if self._detections_published >= MAX_DETECTIONS:
            return

        fx = self._camera_info.k[0]
        fy = self._camera_info.k[4]
        cx = self._camera_info.k[2]
        cy = self._camera_info.k[5]

        x, y, z = POINT_CAM
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
        detection.bbox.size_x = BOX_SIZE_PX
        detection.bbox.size_y = BOX_SIZE_PX

        self._detection_pub.publish(detection)
        self._detections_published += 1


def main():
    rclpy.init()
    node = PointProjectorNode()

    try:
        while rclpy.ok() and node._detections_published < MAX_DETECTIONS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
