import math

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32
from .logic import count_near

DEFAULT_LIMIT = 0.4


def _as_limit(value):
    """Return value as a float limit, or None if it is not a usable number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return None if math.isnan(value) else value


class ScanWatch(Node):
    def __init__(self, **kwargs):
        super().__init__('scan_watch', **kwargs)
        # Dynamic typing so that an edited YAML value such as `limit: 1`
        # (an integer) is accepted as well as `limit: 1.0`.
        self.declare_parameter(
            'limit', DEFAULT_LIMIT,
            ParameterDescriptor(
                description='Count ranges at or below this distance [m]',
                dynamic_typing=True))
        limit = _as_limit(self.get_parameter('limit').value)
        if limit is None:
            raise ValueError(
                f"parameter 'limit' must be a number, got "
                f"{self.get_parameter('limit').value!r}")
        self.limit = limit
        self.add_on_set_parameters_callback(self._on_set_parameters)
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        # Best-effort subscription matches both best-effort and reliable
        # sensor publishers.
        self.sub = self.create_subscription(LaserScan, 'scan', self.receive, qos_profile_sensor_data)
        self.get_logger().info(f'limit={self.limit}')

    def _on_set_parameters(self, params):
        for param in params:
            if param.name != 'limit':
                continue
            limit = _as_limit(param.value)
            if limit is None:
                return SetParametersResult(
                    successful=False, reason="'limit' must be a number")
            self.limit = limit
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
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
