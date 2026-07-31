#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
import message_filters
from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D

POINT_CAM = (0.1, 0.05, 2.0)
MAX_DETECTIONS = 20


class PointProjector(Node):

    def __init__(self):
        super().__init__('point_projector')

        self.detection_pub = self.create_publisher(Detection2D, '/detection', 10)
        self.count = 0

        sensor_qos = QoSProfile(depth=10)
        sensor_qos.reliability = QoSReliabilityPolicy.BEST_EFFORT

        image_sub = message_filters.Subscriber(self, Image, '/camera/image_raw', qos_profile=sensor_qos)
        info_sub = message_filters.Subscriber(self, CameraInfo, '/camera/camera_info', qos_profile=sensor_qos)

        self.sync = message_filters.ApproximateTimeSynchronizer(
            [image_sub, info_sub], queue_size=10, slop=0.1)
        self.sync.registerCallback(self.callback)

    def callback(self, image_msg, info_msg):
        fx = info_msg.k[0]
        fy = info_msg.k[4]
        cx = info_msg.k[2]
        cy = info_msg.k[5]

        x, y, z = POINT_CAM
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
            rclpy.shutdown()


def main():
    rclpy.init()
    node = PointProjector()
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
