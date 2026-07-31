#!/usr/bin/env python3
"""Scenario for the ros2-troubleshooting QoS ladder.

Publishes three topics, each carrying one QoS policy a default subscriber gets
wrong. Every one of these is a SILENT failure: the publisher is healthy,
`ros2 topic hz` shows traffic, and an incompatible subscriber's callback simply
never fires.

  /sensor  BEST_EFFORT + VOLATILE, 20 Hz
           A default rclpy subscriber is RELIABLE, which cannot match a
           BEST_EFFORT offer. This is the README's headline failure.

  /config  RELIABLE + TRANSIENT_LOCAL, depth 1, published ONCE at startup
           and never again. A default VOLATILE subscriber that starts later
           gets nothing, because it never asked for the retained sample.

  /paced   RELIABLE + VOLATILE with DEADLINE 200 ms, 10 Hz
           A subscriber REQUESTING a deadline stricter than the 200 ms offered
           is incompatible. Requesting a looser one, or none, is fine.

Runs until killed.
"""
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32, String

SENSOR_HZ = 20.0
PACED_HZ = 10.0
PACED_DEADLINE_MS = 200


class QoSPublishers(Node):
    def __init__(self):
        super().__init__("qos_publishers")

        sensor_qos = QoSProfile(depth=5,
                                reliability=ReliabilityPolicy.BEST_EFFORT,
                                durability=DurabilityPolicy.VOLATILE)
        self.sensor_pub = self.create_publisher(Int32, "/sensor", sensor_qos)
        self.sensor_n = 0
        self.create_timer(1.0 / SENSOR_HZ, self.pub_sensor)

        config_qos = QoSProfile(depth=1,
                                reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.config_pub = self.create_publisher(String, "/config", config_qos)
        msg = String()
        msg.data = "calibration-7"
        self.config_pub.publish(msg)   # once, at startup, never again

        paced_qos = QoSProfile(
            depth=5,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            deadline=Duration(nanoseconds=PACED_DEADLINE_MS * 1_000_000))
        self.paced_pub = self.create_publisher(Int32, "/paced", paced_qos)
        self.paced_n = 0
        self.create_timer(1.0 / PACED_HZ, self.pub_paced)

        self.get_logger().info(
            "/sensor BEST_EFFORT 20Hz | /config TRANSIENT_LOCAL latched once | "
            f"/paced deadline {PACED_DEADLINE_MS}ms 10Hz")

    def pub_sensor(self):
        m = Int32()
        m.data = self.sensor_n
        self.sensor_n += 1
        self.sensor_pub.publish(m)

    def pub_paced(self):
        m = Int32()
        m.data = self.paced_n
        self.paced_n += 1
        self.paced_pub.publish(m)


def main():
    rclpy.init()
    node = QoSPublishers()
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
