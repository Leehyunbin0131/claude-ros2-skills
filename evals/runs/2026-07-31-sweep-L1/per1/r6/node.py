#!/usr/bin/env python3
import sys

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image


class Annotator(Node):
    def __init__(self):
        super().__init__('annotator')
        self.bridge = CvBridge()
        self.count = 0
        self.max_frames = 20
        self.publisher = self.create_publisher(Image, '/annotated', 10)
        camera_qos = QoSProfile(depth=10)
        camera_qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        camera_qos.durability = QoSDurabilityPolicy.VOLATILE
        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.callback, camera_qos)

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        self.count += 1
        cv2.putText(
            frame, f'frame {self.count}', (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(frame, (frame.shape[1] // 2, frame.shape[0] // 2),
                    20, (0, 0, 255), 3)

        out_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        out_msg.header = msg.header
        self.publisher.publish(out_msg)

        self.get_logger().info(f'FRAME {self.count}')

        if self.count >= self.max_frames:
            rclpy.shutdown()


def main():
    rclpy.init()
    node = Annotator()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()

    sys.exit(0)


if __name__ == '__main__':
    main()
