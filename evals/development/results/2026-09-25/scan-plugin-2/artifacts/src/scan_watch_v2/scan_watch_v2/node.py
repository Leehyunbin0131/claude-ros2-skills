import math
import signal

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32
from .logic import count_near

DEFAULT_LIMIT = 0.42


def _valid_limit(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


class ScanWatch(Node):
    def __init__(self, **kwargs):
        super().__init__('scan_watch_v2', **kwargs)
        # Dynamic typing lets YAML or CLI give an integer such as `limit: 1`;
        # the set-parameters callback still rejects non-numeric values.
        self.declare_parameter(
            'limit', DEFAULT_LIMIT,
            ParameterDescriptor(description='Count ranges at or below this distance [m]',
                                dynamic_typing=True))
        limit = self.get_parameter('limit').value
        if not _valid_limit(limit):
            raise ValueError(f"parameter 'limit' must be a finite number, got {limit!r}")
        self.limit = float(limit)
        self.add_on_set_parameters_callback(self._on_set_parameters)
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        # Sensor-data QoS is best effort, so it matches best-effort and reliable publishers.
        self.sub = self.create_subscription(LaserScan, 'scan', self.receive, qos_profile_sensor_data)
        self.get_logger().info(
            f'counting ranges <= {self.limit} m on {self.sub.topic_name}, '
            f'publishing on {self.pub.topic_name}')

    def _on_set_parameters(self, params):
        for p in params:
            if p.name == 'limit':
                if not _valid_limit(p.value):
                    return SetParametersResult(
                        successful=False, reason="'limit' must be a finite number")
                self.limit = float(p.value)
        return SetParametersResult(successful=True)

    def receive(self, msg):
        result = Int32()
        result.data = count_near(msg.ranges, msg.range_min, msg.range_max, self.limit)
        self.pub.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = ScanWatch()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Ctrl-C under ros2 launch delivers SIGINT twice (terminal and launch);
        # the second must not interrupt cleanup.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        rclpy.try_shutdown()
