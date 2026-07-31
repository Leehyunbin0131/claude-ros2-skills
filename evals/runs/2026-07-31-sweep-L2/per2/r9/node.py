#!/usr/bin/env python3
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from vision_msgs.msg import Detection2D, BoundingBox2D, Pose2D, Point2D

# Fixed 3D point (camera optical frame): X, Y, Z in metres
POINT_3D = (0.1, 0.05, 2.0)

# Placeholder bounding box size in pixels (not specified by the task)
BBOX_SIZE_X = 20.0
BBOX_SIZE_Y = 20.0

DETECTIONS_TARGET = 20


class ProjectionNode(Node):
    def __init__(self):
        super().__init__('projection_node')

        self._k = None
        self._count = 0

        self._detection_pub = self.create_publisher(Detection2D, '/detection', 10)

        self.create_subscription(
            CameraInfo,
            '/camera/camera_info',
            self._camera_info_cb,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self._image_cb,
            qos_profile_sensor_data,
        )

    def _camera_info_cb(self, msg: CameraInfo):
        self._k = msg.k

    def _image_cb(self, msg: Image):
        if self._k is None:
            self.get_logger().warn('No CameraInfo received yet, skipping frame')
            return

        fx = self._k[0]
        cx = self._k[2]
        fy = self._k[4]
        cy = self._k[5]

        x, y, z = POINT_3D
        u = fx * (x / z) + cx
        v = fy * (y / z) + cy

        self.get_logger().info(f'PIXEL {u} {v}')

        detection = Detection2D()
        detection.header = msg.header

        bbox = BoundingBox2D()
        center = Pose2D()
        center.position = Point2D(x=u, y=v)
        center.theta = 0.0
        bbox.center = center
        bbox.size_x = BBOX_SIZE_X
        bbox.size_y = BBOX_SIZE_Y
        detection.bbox = bbox

        self._detection_pub.publish(detection)

        self._count += 1
        if self._count >= DETECTIONS_TARGET:
            self.get_logger().info(f'Published {self._count} detections, shutting down')
            rclpy.shutdown()


def main():
    rclpy.init()
    node = ProjectionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    sys.exit(0)


if __name__ == '__main__':
    main()
