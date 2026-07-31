#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


class StaticTfNode(Node):
    def __init__(self):
        super().__init__('static_tf_node')

        self.declare_parameter('tx', 0.2)
        self.declare_parameter('ty', 0.0)
        self.declare_parameter('tz', 0.1)

        tx = self.get_parameter('tx').get_parameter_value().double_value
        ty = self.get_parameter('ty').get_parameter_value().double_value
        tz = self.get_parameter('tz').get_parameter_value().double_value

        self.tf_broadcaster = StaticTransformBroadcaster(self)

        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_link'
        t.child_frame_id = 'sensor_link'
        t.transform.translation.x = tx
        t.transform.translation.y = ty
        t.transform.translation.z = tz
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(t)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.timer = self.create_timer(0.1, self.on_timer)

    def on_timer(self):
        try:
            trans = self.tf_buffer.lookup_transform(
                'base_link', 'sensor_link', rclpy.time.Time())
        except TransformException as ex:
            self.get_logger().debug(f'Could not look up transform: {ex}')
            return

        x = trans.transform.translation.x
        y = trans.transform.translation.y
        z = trans.transform.translation.z
        self.get_logger().info(f'TF {x} {y} {z}')

        self.timer.cancel()
        rclpy.shutdown()


def main():
    rclpy.init()
    node = StaticTfNode()
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
