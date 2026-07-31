#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

# Fixed 3D point in the camera optical frame (metres)
POINT_3D = (0.1, 0.05, 2.0)

MAX_DETECTIONS = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('projection_node')

        self._camera_info = None
        self._count = 0

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._camera_info_cb,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self._image_cb,
            qos_profile_sensor_data)

    def _camera_info_cb(self, msg: CameraInfo):
        self._camera_info = msg

    def _image_cb(self, msg: Image):
        if self._camera_info is None:
            return

        k = self._camera_info.k
        fx, cx = k[0], k[2]
        fy, cy = k[4], k[5]

        x, y, z = POINT_3D
        u = fx * (x / z) + cx
        v = fy * (y / z) + cy

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
        bbox.size_x = 0.0
        bbox.size_y = 0.0
        detection.bbox = bbox

        self._detection_pub.publish(detection)

        self._count += 1
        if self._count >= MAX_DETECTIONS:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = ProjectionNode()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()

    sys.exit(0)


if __name__ == '__main__':
    main()
