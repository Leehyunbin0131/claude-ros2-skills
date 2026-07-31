#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

# Fixed 3D point in the camera optical frame.
POINT_CAMERA = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class ProjectorNode(Node):
    def __init__(self):
        super().__init__('projector_node')
        self.camera_info = None
        self.detection_count = 0

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 10)
        self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)

    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def image_callback(self, msg: Image):
        if self.camera_info is None:
            return

        k = self.camera_info.k
        fx, fy = k[0], k[4]
        cx, cy = k[2], k[5]

        x, y, z = POINT_CAMERA
        u = fx * (x / z) + cx
        v = fy * (y / z) + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header
        detection.bbox = BoundingBox2D()
        detection.bbox.center = Pose2D()
        detection.bbox.center.position = Point2D()
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 0.0
        detection.bbox.size_y = 0.0

        self.detection_pub.publish(detection)
        self.detection_count += 1

        if self.detection_count >= MAX_DETECTIONS:
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = ProjectorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
