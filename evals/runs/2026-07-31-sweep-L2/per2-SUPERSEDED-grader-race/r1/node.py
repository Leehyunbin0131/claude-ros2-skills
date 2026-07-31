#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

# Fixed 3D point in the camera optical frame.
POINT_3D = (0.1, 0.05, 2.0)

MAX_DETECTIONS = 20


class ProjectorNode(Node):
    def __init__(self):
        super().__init__('point_projector')

        self._camera_info = None
        self._detection_count = 0

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self._camera_info_cb, 10)
        self.create_subscription(
            Image, '/camera/image_raw', self._image_cb, 10)

    def _camera_info_cb(self, msg: CameraInfo):
        self._camera_info = msg

    def _image_cb(self, msg: Image):
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
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 0.0
        detection.bbox.size_y = 0.0

        self.detection_pub.publish(detection)
        self._detection_count += 1

        if self._detection_count >= MAX_DETECTIONS:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = ProjectorNode()
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
