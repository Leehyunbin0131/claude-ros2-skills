#!/usr/bin/env python3
"""The broken subscriber from Task 3: default depth-10 RELIABLE on a
BEST_EFFORT topic.

Run alongside fake_camera_pub.py. `ros2 topic hz /camera/image_raw` shows
30 Hz, this node's callback never fires, and nothing in the logs looks like an
error. Prints its received count every second so the silence is measurable
rather than inferred.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class ReliableSub(Node):
    def __init__(self):
        super().__init__("reliable_image_sub")
        self.count = 0
        # Depth-only overload == RELIABLE/VOLATILE/KEEP_LAST: the default an
        # agent reaches for when it does not think about sensor QoS.
        self.create_subscription(Image, "/camera/image_raw", self.on_image, 10)
        self.create_timer(1.0, self.report)

    def on_image(self, _msg):
        self.count += 1

    def report(self):
        self.get_logger().info(f"images received: {self.count}")


def main():
    rclpy.init()
    node = ReliableSub()
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
