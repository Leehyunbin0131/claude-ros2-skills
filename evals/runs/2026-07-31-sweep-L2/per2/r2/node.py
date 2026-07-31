#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

POINT_CAMERA = (0.1, 0.05, 2.0)
TARGET_COUNT = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('projection_node')

        self.camera_info = None
        self.detection_count = 0

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo, '/camera/camera_info', self.camera_info_callback,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, '/camera/image_raw', self.image_callback,
            qos_profile_sensor_data)

    def camera_info_callback(self, msg):
        self.camera_info = msg

    def image_callback(self, msg):
        if self.camera_info is None:
            return

        k = self.camera_info.k
        fx, cx = k[0], k[2]
        fy, cy = k[4], k[5]

        x, y, z = POINT_CAMERA
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
        self.detection_count += 1

        if self.detection_count >= TARGET_COUNT:
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
