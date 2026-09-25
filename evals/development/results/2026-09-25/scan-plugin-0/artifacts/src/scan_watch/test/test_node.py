"""Run the real ScanWatch callback over DDS with a best-effort publisher."""
import math
import os
import time
import uuid

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

from scan_watch.node import ScanWatch

YAML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config', 'monitor.yaml')


@pytest.fixture
def context():
    ctx = rclpy.Context()
    rclpy.init(context=ctx, args=['--ros-args', '--params-file', YAML_PATH])
    yield ctx
    rclpy.shutdown(context=ctx)


def _scan(ranges, range_min=0.1, range_max=10.0):
    msg = LaserScan()
    msg.range_min = range_min
    msg.range_max = range_max
    msg.ranges = ranges
    return msg


class Harness:
    def __init__(self, context, **node_kwargs):
        ns = 'test_' + uuid.uuid4().hex[:8]
        self.ns = ns
        self.watch = ScanWatch(context=context, namespace=ns, **node_kwargs)
        self.probe = Node('probe', context=context, namespace=ns)
        self.pub = self.probe.create_publisher(
            LaserScan, 'scan',
            QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.received = []
        self.probe.create_subscription(
            Int32, 'near_count', lambda m: self.received.append(m.data), 10)
        self.executor = SingleThreadedExecutor(context=context)
        self.executor.add_node(self.watch)
        self.executor.add_node(self.probe)
        self._wait(lambda: self.pub.get_subscription_count() >= 1
                   and self.probe.count_publishers(f'/{ns}/near_count') >= 1)

    def _wait(self, cond, timeout=10.0):
        deadline = time.monotonic() + timeout
        while not cond():
            assert time.monotonic() < deadline, 'timed out'
            self.executor.spin_once(timeout_sec=0.05)

    def send(self, msg):
        before = len(self.received)
        self.pub.publish(msg)
        self._wait(lambda: len(self.received) > before)
        return self.received[-1]

    def close(self):
        self.executor.shutdown()
        self.watch.destroy_node()
        self.probe.destroy_node()


def test_yaml_default_limit_and_namespaced_topics(context):
    h = Harness(context)
    try:
        assert h.watch.get_parameter('limit').value == pytest.approx(0.4)
        assert h.watch.get_namespace() == '/' + h.ns
        assert h.probe.count_subscribers(f'/{h.ns}/scan') == 1
        # 0.4 counts (inclusive); 0.05 < range_min; nan/inf ignored.
        msg = _scan([0.05, 0.2, 0.4, 0.5, math.nan, math.inf, -math.inf])
        assert h.send(msg) == 2
        assert h.send(_scan([])) == 0
    finally:
        h.close()


def test_override_and_runtime_parameter_change(context):
    h = Harness(context, parameter_overrides=[Parameter('limit', value=0.8)])
    try:
        msg = _scan([0.2, 0.4, 0.8, 0.9, 12.0], range_max=10.0)
        assert h.send(msg) == 3
        h.watch.set_parameters([Parameter('limit', value=1)])  # int accepted
        assert h.send(msg) == 4
        result = h.watch.set_parameters([Parameter('limit', value='far')])
        assert not result[0].successful
        assert h.send(msg) == 4
    finally:
        h.close()
