#!/usr/bin/env python3
"""Republish Gazebo's bridged IMU reading on /imu with frame_id set to the
mounting link's name, since gz-sim always stamps it as "<model>/<link>/<sensor>"
instead."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


class ImuFrameFix(Node):

    def __init__(self):
        super().__init__('imu_frame_fix')
        self.declare_parameter('frame_id', 'imu_link')
        self.frame_id = self.get_parameter('frame_id').value
        self.pub = self.create_publisher(Imu, '/imu', 10)
        self.sub = self.create_subscription(Imu, '/imu/raw', self.on_imu, 10)

    def on_imu(self, msg):
        msg.header.frame_id = self.frame_id
        self.pub.publish(msg)


def main():
    rclpy.init()
    rclpy.spin(ImuFrameFix())


if __name__ == '__main__':
    main()
