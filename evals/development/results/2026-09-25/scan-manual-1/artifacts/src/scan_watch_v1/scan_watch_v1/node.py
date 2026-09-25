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

DEFAULT_LIMIT = 0.41


class ScanWatch(Node):
    def __init__(self, **kwargs):
        super().__init__('scan_watch_v1', **kwargs)
        # Registered before declaring so the initial (YAML / override) value is validated too.
        self.add_on_set_parameters_callback(self._validate_params)
        # dynamic_typing lets an integer such as `limit: 1` be accepted; it is read as float.
        self.declare_parameter(
            'limit', DEFAULT_LIMIT,
            ParameterDescriptor(description='Count ranges at or below this distance [m]',
                                dynamic_typing=True))
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        # Sensor-data QoS is best effort, which matches both best-effort and reliable publishers.
        self.sub = self.create_subscription(LaserScan, 'scan', self.receive, qos_profile_sensor_data)
        self.get_logger().info(f'limit={self.limit():.3f}')

    def _validate_params(self, params):
        for p in params:
            if p.name != 'limit':
                continue
            if p.type_ not in (Parameter.Type.DOUBLE, Parameter.Type.INTEGER) \
                    or not math.isfinite(p.value):
                return SetParametersResult(
                    successful=False, reason='limit must be a finite number')
        return SetParametersResult(successful=True)

    def limit(self):
        return float(self.get_parameter('limit').value)

    def receive(self, msg):
        result = Int32()
        result.data = count_near(msg.ranges, msg.range_min, msg.range_max, self.limit())
        self.pub.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = ScanWatch()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Already shutting down: a repeated Ctrl-C (terminal + ros2 launch both send
        # SIGINT) must not interrupt cleanup.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        rclpy.try_shutdown()
