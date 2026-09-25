import math
import signal

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

from .logic import count_near

DEFAULT_LIMIT = 0.43


def _limit_error(value):
    """Return an error string if value is not a usable limit, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f'limit must be a number, got {value!r}'
    if math.isnan(value):
        return 'limit must not be NaN'
    return None


class ScanWatch(Node):
    def __init__(self, **kwargs):
        super().__init__('scan_watch_v3', **kwargs)
        # Dynamic typing so that an integer such as `limit: 1` in YAML is accepted.
        self.declare_parameter(
            'limit', DEFAULT_LIMIT,
            ParameterDescriptor(
                description='Count ranges at or below this distance [m]',
                dynamic_typing=True))
        error = _limit_error(self.get_parameter('limit').value)
        if error:
            raise ValueError(error)
        self.add_on_set_parameters_callback(self._on_set_parameters)
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        # Best-effort subscription: matches both best-effort and reliable sensor publishers.
        self.sub = self.create_subscription(
            LaserScan, 'scan', self.receive, qos_profile_sensor_data)
        self.get_logger().info(
            f'Counting ranges <= {self.limit()} m on {self.sub.topic_name}, '
            f'publishing on {self.pub.topic_name}')

    def limit(self):
        return float(self.get_parameter('limit').value)

    def _on_set_parameters(self, params):
        for param in params:
            if param.name == 'limit':
                value = None if param.type_ == Parameter.Type.NOT_SET else param.value
                error = _limit_error(value)
                if error:
                    return SetParametersResult(successful=False, reason=error)
        return SetParametersResult(successful=True)

    def receive(self, msg):
        result = Int32()
        result.data = count_near(msg.ranges, msg.range_min, msg.range_max, self.limit())
        self.pub.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ScanWatch()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # ros2 launch forwards SIGINT on top of the terminal's own Ctrl-C;
        # ignore the repeat so it does not interrupt cleanup.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
