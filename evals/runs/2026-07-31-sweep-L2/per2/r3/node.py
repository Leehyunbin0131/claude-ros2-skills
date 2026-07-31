#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import (
    Detection2D,
    BoundingBox2D,
    Pose2D,
    Point2D,
    ObjectHypothesisWithPose,
    ObjectHypothesis,
)

POINT_3D = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20
BOX_SIZE = 20.0


class PointProjectorNode(Node):
    def __init__(self):
        super().__init__('point_projector')

        self.camera_info = None
        self.detection_count = 0

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback, 10
        )
        self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10
        )

    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def image_callback(self, msg: Image):
        if self.detection_count >= MAX_DETECTIONS:
            return
        if self.camera_info is None:
            return

        k = self.camera_info.k
        fx, fy = k[0], k[4]
        cx, cy = k[2], k[5]

        x, y, z = POINT_3D
        u = fx * x / z + cx
        v = fy * y / z + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header

        bbox = BoundingBox2D()
        center = Pose2D()
        position = Point2D()
        position.x = u
        position.y = v
        center.position = position
        center.theta = 0.0
        bbox.center = center
        bbox.size_x = BOX_SIZE
        bbox.size_y = BOX_SIZE
        detection.bbox = bbox

        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis = ObjectHypothesis()
        hypothesis.hypothesis.class_id = 'projected_point'
        hypothesis.hypothesis.score = 1.0
        detection.results.append(hypothesis)

        self.detection_pub.publish(detection)
        self.detection_count += 1

        if self.detection_count >= MAX_DETECTIONS:
            self.get_logger().info(f'Published {MAX_DETECTIONS} detections, shutting down.')
            rclpy.shutdown()


def main():
    rclpy.init()
    node = PointProjectorNode()
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
