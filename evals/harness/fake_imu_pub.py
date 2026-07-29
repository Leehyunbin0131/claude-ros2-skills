#!/usr/bin/env python3
"""Stand-in for an IMU driver on a robot whose IMU is mounted wrong.

Exists so v2 Task 2 can be graded against a running system without a robot. The
one property that matters: the robot is **at rest and level**, so gravity must
appear as ~+9.81 m/s^2 on `linear_acceleration.z` (REP 103). Here it appears on
**+X** instead, which is what a 90-degree rotated mount produces.

That is the bug the task is about, and it is only discoverable by sampling the
topic — nothing in the URDF, the logs, or any web search can tell you how a
particular robot's IMU is physically bolted on. This is category 2 in
DESIGN.md: not reachable, at all, by any means except measuring.

Noise is small and zero-mean so a handful of samples is enough to see it; an
agent that reads one message or a hundred reaches the same conclusion.

Field names and the QoS profile were read from the installed Jazzy packages
(`ros2 interface show sensor_msgs/msg/Imu`, `rclpy.qos`).

Usage:  python3 fake_imu_pub.py [--topic /imu/data]
"""
import argparse
import math
import random

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

G = 9.81
NOISE = 0.05  # m/s^2, well inside check_imu_gravity.py's 1.5 tolerance


class FakeImu(Node):
    """Publishes a stationary, level robot whose IMU is rotated 90 deg about Y.

    Gravity therefore reads on +X. `check_imu_gravity.py` should FAIL on this,
    naming X as the dominant axis.
    """

    def __init__(self, topic: str, rate_hz: float):
        super().__init__("fake_imu_pub")
        self.pub = self.create_publisher(Imu, topic, qos_profile_sensor_data)
        self.timer = self.create_timer(1.0 / rate_hz, self.tick)
        self.get_logger().info(
            f"publishing {topic} — stationary robot, gravity on +X "
            f"(a 90 deg rotated mount). Correct answer: the IMU is misaligned."
        )

    def tick(self) -> None:
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "imu_link"

        # Identity orientation: the driver reports "level", which is exactly why
        # this is silent — orientation looks right, acceleration does not.
        msg.orientation.w = 1.0

        # The bug: gravity on +X instead of +Z.
        msg.linear_acceleration.x = G + random.gauss(0.0, NOISE)
        msg.linear_acceleration.y = random.gauss(0.0, NOISE)
        msg.linear_acceleration.z = random.gauss(0.0, NOISE)

        # At rest: no rotation.
        msg.angular_velocity.x = random.gauss(0.0, 0.002)
        msg.angular_velocity.y = random.gauss(0.0, 0.002)
        msg.angular_velocity.z = random.gauss(0.0, 0.002)

        # -1 in the first element of a covariance means "unknown", per the
        # sensor_msgs/Imu docs; report a real (small) covariance instead.
        for i in (0, 4, 8):
            msg.linear_acceleration_covariance[i] = NOISE ** 2
            msg.angular_velocity_covariance[i] = 1e-5
        msg.orientation_covariance[0] = -1.0

        self.pub.publish(msg)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic", default="/imu/data")
    ap.add_argument("--rate", type=float, default=50.0)
    args = ap.parse_args()

    rclpy.init()
    node = FakeImu(args.topic, args.rate)
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
