#!/usr/bin/env python3
"""Minimal joint state publisher for the simple_arm robot.

Publishes a fixed JointState (all zeros) at a steady rate so that
MoveIt's CurrentStateMonitor always has a valid, complete robot state
to plan from, without depending on any real or simulated hardware.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

JOINT_NAMES = ["joint1", "joint2", "joint3"]


class FakeJointStatePublisher(Node):
    def __init__(self):
        super().__init__("fake_joint_state_publisher")
        self.publisher = self.create_publisher(JointState, "joint_states", 10)
        self.positions = [0.0 for _ in JOINT_NAMES]
        self.timer = self.create_timer(0.1, self.tick)

    def tick(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = JOINT_NAMES
        msg.position = self.positions
        msg.velocity = [0.0 for _ in JOINT_NAMES]
        msg.effort = [0.0 for _ in JOINT_NAMES]
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = FakeJointStatePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
