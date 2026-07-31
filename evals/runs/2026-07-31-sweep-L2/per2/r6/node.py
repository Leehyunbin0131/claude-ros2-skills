#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

# Fixed 3D point in the camera optical frame to project each frame.
POINT_CAMERA = (0.1, 0.05, 2.0)


class ProjectorNode(Node):

    def __init__(self):
        super().__init__('point_projector')

        self.camera_info = None
        self.count = 0
        self.max_detections = 20

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo,
            '/camera/camera_info',
            self.camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            qos_profile_sensor_data,
        )

    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def image_callback(self, msg: Image):
        if self.camera_info is None or self.count >= self.max_detections:
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
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 0.0
        detection.bbox.size_y = 0.0

        self.detection_pub.publish(detection)
        self.count += 1


def main():
    rclpy.init()
    node = ProjectorNode()

    try:
        while rclpy.ok() and node.count < node.max_detections:
            rclpy.spin_once(node, timeout_sec=1.0)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
