#!/usr/bin/env python3
"""Stand-in for a camera driver: /camera/image_raw at 30 Hz, BEST_EFFORT.

Reproduces the exact premise of Task 3 — `ros2 topic hz` reports 30 Hz while a
default (RELIABLE) subscriber receives nothing. Reliability is set explicitly
rather than via a named profile so the offer is unambiguous in the transcript.

Symbols verified against the installed Jazzy packages
(`ros2 interface show sensor_msgs/msg/Image`, `rclpy.qos`).
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

WIDTH, HEIGHT = 64, 48  # tiny: the point is the QoS offer, not the pixels


class FakeCamera(Node):
    def __init__(self):
        super().__init__("fake_camera_pub")
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.pub = self.create_publisher(Image, "/camera/image_raw", qos)
        self.create_timer(1.0 / 30.0, self.tick)
        self.get_logger().info("publishing /camera/image_raw at 30 Hz (BEST_EFFORT)")

    def tick(self):
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_optical_frame"
        msg.height = HEIGHT
        msg.width = WIDTH
        msg.encoding = "mono8"
        msg.is_bigendian = 0
        msg.step = WIDTH
        msg.data = bytes(WIDTH * HEIGHT)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FakeCamera()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
