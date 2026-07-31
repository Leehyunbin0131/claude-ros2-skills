#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

POINT_CAMERA = (0.1, 0.05, 2.0)
TARGET_DETECTIONS = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('node')
        self.camera_info = None
        self.detection_count = 0

        self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, qos_profile_sensor_data)
        self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback,
            qos_profile_sensor_data)
        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

    def camera_info_callback(self, msg):
        self.camera_info = msg

    def image_callback(self, msg):
        if self.camera_info is None:
            return

        k = self.camera_info.k
        fx, fy = k[0], k[4]
        cx, cy = k[2], k[5]

        x, y, z = POINT_CAMERA
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
        detection.bbox.size_x = 10.0
        detection.bbox.size_y = 10.0

        self.detection_pub.publish(detection)
        self.detection_count += 1

        if self.detection_count >= TARGET_DETECTIONS:
            self.get_logger().info(f'Published {TARGET_DETECTIONS} detections, shutting down')
            rclpy.shutdown()


def main():
    rclpy.init()
    node = ProjectionNode()
    try:
        while rclpy.ok():
            rclpy.spin_once(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
