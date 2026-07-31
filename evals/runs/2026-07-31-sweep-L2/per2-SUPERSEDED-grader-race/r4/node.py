#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

# Fixed 3D point in the camera optical frame (metres).
POINT_CAMERA = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('projection_node')

        self._camera_info = None
        self._detection_count = 0

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._camera_info_callback,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self._image_callback,
            qos_profile_sensor_data)

    def _camera_info_callback(self, msg: CameraInfo):
        self._camera_info = msg

    def _image_callback(self, msg: Image):
        if self._camera_info is None:
            return

        k = self._camera_info.k
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
        detection.bbox.center.position = Point2D(x=u, y=v)
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 0.0
        detection.bbox.size_y = 0.0

        self._detection_pub.publish(detection)
        self._detection_count += 1

        if self._detection_count >= MAX_DETECTIONS:
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
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
