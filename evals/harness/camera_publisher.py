#!/usr/bin/env python3
"""Camera scenario for the ros2-perception ladder.

Default mode (per1, per2):
  /camera/image_raw    sensor_msgs/msg/Image, bgr8, 160x120, 20 Hz
  /camera/camera_info  sensor_msgs/msg/CameraInfo, same rate

--depth mode (per3):
  /depth/image_raw     sensor_msgs/msg/Image, 16UC1, MILLIMETRES, 160x120, 20 Hz
  /depth/camera_info   sensor_msgs/msg/CameraInfo, same rate

Both publish with BEST_EFFORT reliability, which is what real camera drivers do
and what `image_transport` expects. A default rclpy subscriber is RELIABLE and
will never match -- that trap is part of the terrain, not an accident.

The depth frame deliberately contains invalid pixels: 16UC1 depth uses 0 to mean
"no return", and a naive conversion turns those into a wall of points at the
camera origin. Roughly a fifth of the frame is zeros for that reason.

Intrinsics are a plain pinhole model with no distortion, so a correct projection
of a known 3D point has one right answer:

    fx = fy = 100.0, cx = 80.0, cy = 60.0

    (0.1, 0.05, 2.0) -> u = 100*0.1/2.0 + 80 = 85.0
                        v = 100*0.05/2.0 + 60 = 62.5

P and K carry the same values here; that is deliberate. per2 grades the pixel,
not which matrix was read, so a cell that picks either is correct and the check
cannot punish a defensible choice.

Runs until killed.
"""
import argparse

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image

WIDTH, HEIGHT = 160, 120
HZ = 20.0
FX = FY = 100.0
CX, CY = 80.0, 60.0


def camera_info(frame_id: str) -> CameraInfo:
    ci = CameraInfo()
    ci.width = WIDTH
    ci.height = HEIGHT
    ci.distortion_model = "plumb_bob"
    ci.d = [0.0, 0.0, 0.0, 0.0, 0.0]
    ci.k = [FX, 0.0, CX,
            0.0, FY, CY,
            0.0, 0.0, 1.0]
    ci.r = [1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0]
    ci.p = [FX, 0.0, CX, 0.0,
            0.0, FY, CY, 0.0,
            0.0, 0.0, 1.0, 0.0]
    ci.header.frame_id = frame_id
    return ci


class CameraPublisher(Node):
    def __init__(self, depth: bool):
        super().__init__("camera_publisher")
        self.depth = depth
        self.n = 0

        qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        base = "/depth" if depth else "/camera"
        self.frame_id = "depth_optical_frame" if depth else "camera_optical_frame"
        self.img_pub = self.create_publisher(Image, f"{base}/image_raw", qos)
        self.info_pub = self.create_publisher(CameraInfo, f"{base}/camera_info", qos)
        self.info = camera_info(self.frame_id)
        self.create_timer(1.0 / HZ, self.tick)
        self.get_logger().info(
            f"{base}/image_raw {'16UC1 mm depth' if depth else 'bgr8'} "
            f"{WIDTH}x{HEIGHT} @ {HZ:g} Hz BEST_EFFORT")

    def make_depth(self) -> Image:
        # Millimetres, uint16. A slanted ramp from 0.5 m to 3.0 m, with the left
        # fifth of the frame zeroed to mean "no return".
        cols = np.linspace(500, 3000, WIDTH, dtype=np.float32)
        frame = np.tile(cols, (HEIGHT, 1)).astype(np.uint16)
        frame[:, : WIDTH // 5] = 0
        msg = Image()
        msg.height, msg.width = HEIGHT, WIDTH
        msg.encoding = "16UC1"
        msg.is_bigendian = 0
        msg.step = WIDTH * 2
        msg.data = frame.tobytes()
        return msg

    def make_bgr(self) -> Image:
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:, :, 0] = (self.n * 3) % 256      # B, drifts so frames differ
        frame[:, :, 1] = 128
        frame[HEIGHT // 3: 2 * HEIGHT // 3, WIDTH // 3: 2 * WIDTH // 3, 2] = 255
        msg = Image()
        msg.height, msg.width = HEIGHT, WIDTH
        msg.encoding = "bgr8"
        msg.is_bigendian = 0
        msg.step = WIDTH * 3
        msg.data = frame.tobytes()
        return msg

    def tick(self):
        stamp = self.get_clock().now().to_msg()
        msg = self.make_depth() if self.depth else self.make_bgr()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        self.info.header.stamp = stamp
        self.img_pub.publish(msg)
        self.info_pub.publish(self.info)
        self.n += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", action="store_true",
                    help="publish 16UC1 depth on /depth instead of bgr8 on /camera")
    args = ap.parse_args()

    rclpy.init()
    node = CameraPublisher(args.depth)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
