#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import message_filters

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

POINT_CAMERA = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('image_point_projector')

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.image_sub = message_filters.Subscriber(
            self, Image, '/camera/image_raw', qos_profile=qos_profile_sensor_data)
        self.info_sub = message_filters.Subscriber(
            self, CameraInfo, '/camera/camera_info', qos_profile=qos_profile_sensor_data)

        self.sync = message_filters.ApproximateTimeSynchronizer(
            [self.image_sub, self.info_sub], queue_size=10, slop=0.1)
        self.sync.registerCallback(self.callback)

        self.count = 0

    def callback(self, image_msg: Image, info_msg: CameraInfo):
        fx = info_msg.k[0]
        fy = info_msg.k[4]
        cx = info_msg.k[2]
        cy = info_msg.k[5]

        x, y, z = POINT_CAMERA
        u = fx * x / z + cx
        v = fy * y / z + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = image_msg.header
        detection.bbox.center.position.x = u
        detection.bbox.center.position.y = v
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = 0.0
        detection.bbox.size_y = 0.0

        self.detection_pub.publish(detection)

        self.count += 1
        if self.count >= MAX_DETECTIONS:
            self.get_logger().info(f'Published {self.count} detections, shutting down.')
            rclpy.shutdown()


def main():
    rclpy.init()
    node = ProjectionNode()
    rclpy.spin(node)
    node.destroy_node()
    sys.exit(0)


if __name__ == '__main__':
    main()
