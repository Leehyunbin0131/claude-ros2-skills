"""Publish the normalized temperature for every reading."""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64

from thermal_interfaces.msg import ThermalReading

from .conversion import normalize


class Monitor(Node):

    def __init__(self):
        super().__init__('thermal_py_monitor')
        self._publisher = self.create_publisher(Float64, 'monitor/py_temperature_c', 10)
        self._subscription = self.create_subscription(
            ThermalReading, 'sensor/thermal', self._on_reading, 10)

    def _on_reading(self, msg):
        self._publisher.publish(Float64(data=float(normalize(msg))))


def main(args=None):
    rclpy.init(args=args)
    node = Monitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
