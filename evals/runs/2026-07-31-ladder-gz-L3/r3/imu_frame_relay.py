#!/usr/bin/env python3
# Gazebo's IMU sensor stamps its message frame_id with a scoped
# "model/link/sensor" path with no override hook. This relay republishes
# the bridged IMU data with frame_id set to the URDF link the sensor is
# mounted on.
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


class ImuFrameRelay(Node):
    def __init__(self):
        super().__init__('imu_frame_relay')
        self.declare_parameter('frame_id', 'imu_link')
        self._frame_id = self.get_parameter('frame_id').value
        self._pub = self.create_publisher(Imu, 'imu', 10)
        self._sub = self.create_subscription(Imu, 'imu/raw', self._callback, 10)

    def _callback(self, msg):
        msg.header.frame_id = self._frame_id
        self._pub.publish(msg)


def main():
    rclpy.init()
    node = ImuFrameRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
