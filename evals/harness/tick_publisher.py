#!/usr/bin/env python3
"""Scenario for the executor ladder rung L2: publishes `/tick`
(`std_msgs/msg/Int32`) at 1 Hz.

Each tick is meant to trigger one ~1 s service call in the cell under test, so
the callback the cell writes is busy roughly as often as it is invoked. That is
the condition under which a shared MutuallyExclusiveCallbackGroup starves the
cell's own 10 Hz heartbeat timer -- which is what `tr2_heartbeat_steady`
measures.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class Ticker(Node):
    def __init__(self):
        super().__init__("tick_publisher")
        self.pub = self.create_publisher(Int32, "/tick", 10)
        self.n = 0
        self.create_timer(1.0, self.tick)
        self.get_logger().info("/tick up at 1 Hz")

    def tick(self):
        msg = Int32()
        msg.data = self.n
        self.n += 1
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = Ticker()
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
