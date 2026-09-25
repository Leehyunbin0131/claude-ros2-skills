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
    def __init__(self):
        super().__init__('scan_watch')
        self.add_on_set_parameters_callback(self._on_set_parameters)
        # Dynamic typing so that integer values such as `limit: 1` are accepted.
        self.declare_parameter(
            'limit', DEFAULT_LIMIT,
            ParameterDescriptor(description='Count ranges at or below this distance [m]',
                                dynamic_typing=True))
        self.limit = _as_limit(self.get_parameter('limit').value)
        if self.limit is None:
            raise ValueError(f"parameter 'limit' must be a number, got "
                             f"{self.get_parameter('limit').value!r}")
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        # Best-effort sensor QoS matches both best-effort and reliable publishers.
        self.sub = self.create_subscription(LaserScan, 'scan', self.receive, qos_profile_sensor_data)
        self.get_logger().info(
            f'Counting ranges <= {self.limit} from {self.sub.topic_name} '
            f'-> {self.pub.topic_name}')

    def _on_set_parameters(self, params):
        for param in params:
            if param.name == 'limit':
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
    node = None
    try:
        node = ScanWatch()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
