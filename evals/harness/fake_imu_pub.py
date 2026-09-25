#!/usr/bin/env python3
"""Stand-in for an IMU driver on a robot whose IMU is mounted wrong.

Exists so v2 Task 2 can be graded against a running system without a robot. The
one property that matters: the robot is **at rest and level**, so gravity must
appear as ~+9.81 m/s^2 on +Z AFTER transforming to base_link. This fixture
declares an aligned imu_link in TF but reports gravity on +X: the declared
mount and measured acceleration disagree.

That is the bug the task is about, and it is only discoverable by sampling the
topic — nothing in the URDF, the logs, or any web search can tell you how a
particular robot's IMU is physically bolted on.

Noise is small and zero-mean so a handful of samples is enough to see it; an
agent that reads one message or a hundred reaches the same conclusion.

Field names and the QoS profile were read from the installed Jazzy packages
(`ros2 interface show sensor_msgs/msg/Imu`, `rclpy.qos`).

Usage:  python3 fake_imu_pub.py [--topic /imu/data]
"""
import argparse
import random

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster

G = 9.81
NOISE = 0.05  # m/s^2, well inside check_imu_gravity.py's 1.5 tolerance


class FakeImu(Node):
    """Publishes a stationary, level robot whose IMU is rotated 90 deg about Y.

    Gravity therefore reads on +X. `check_imu_gravity.py` should FAIL on this,
    naming X as the dominant axis.
    """

    def __init__(self, topic: str, rate_hz: float):
        super().__init__("fake_imu_pub")
        self.mount = StaticTransformBroadcaster(self)
        transform = TransformStamped()
        transform.header.frame_id = "base_link"
        transform.child_frame_id = "imu_link"
        transform.transform.rotation.w = 1.0
        self.mount.sendTransform(transform)
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

        # Orientation is unavailable (covariance[0] = -1), so consumers must
        # not interpret this placeholder quaternion as a level measurement.
        msg.orientation.w = 1.0

        # The bug: gravity on +X instead of +Z.
        msg.linear_acceleration.x = G + random.gauss(0.0, NOISE)
        msg.linear_acceleration.y = random.gauss(0.0, NOISE)
        msg.linear_acceleration.z = random.gauss(0.0, NOISE)

        # At rest: no rotation.
        msg.angular_velocity.x = random.gauss(0.0, 0.002)
        msg.angular_velocity.y = random.gauss(0.0, 0.002)
        msg.angular_velocity.z = random.gauss(0.0, 0.002)

        # -1 means this quantity is unavailable; all zeros means covariance
        # unknown. Acceleration and angular velocity are available here.
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
