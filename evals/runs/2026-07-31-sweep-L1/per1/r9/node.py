#!/usr/bin/env python3
import sys

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

MAX_FRAMES = 20


class AnnotatorNode(Node):
    def __init__(self):
        super().__init__('annotator_node')
        self.bridge = CvBridge()
        self.frame_count = 0
        self.publisher = self.create_publisher(Image, '/annotated', 10)
        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        self.frame_count += 1
        cv2.circle(frame, (50, 50), 20, (0, 0, 255), -1)
        cv2.putText(frame, f'frame {self.frame_count}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        out_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        out_msg.header = msg.header
        self.publisher.publish(out_msg)

        self.get_logger().info(f'FRAME {self.frame_count}')

        if self.frame_count >= MAX_FRAMES:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = AnnotatorNode()
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
