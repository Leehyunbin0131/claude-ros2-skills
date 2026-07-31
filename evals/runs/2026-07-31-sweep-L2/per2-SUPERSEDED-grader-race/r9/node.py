#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

POINT_3D = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('projection_node')
        self.camera_info = None
        self.detection_count = 0

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 10)
        self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)
        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

    def camera_info_callback(self, msg):
        self.camera_info = msg

    def image_callback(self, msg):
        if self.camera_info is None or self.detection_count >= MAX_DETECTIONS:
            return

        k = self.camera_info.k
        fx, fy, cx, cy = k[0], k[4], k[2], k[5]

        x, y, z = POINT_3D
        u = fx * x / z + cx
        v = fy * y / z + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header

        position = Point2D()
        position.x = u
        position.y = v

        center = Pose2D()
        center.position = position
        center.theta = 0.0

        bbox = BoundingBox2D()
        bbox.center = center
        bbox.size_x = 20.0
        bbox.size_y = 20.0
        detection.bbox = bbox

        self.detection_pub.publish(detection)
        self.detection_count += 1


def main():
    rclpy.init()
    node = ProjectionNode()
    try:
        while rclpy.ok() and node.detection_count < MAX_DETECTIONS:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
