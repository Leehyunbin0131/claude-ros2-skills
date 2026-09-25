import math
import os
import time
import uuid

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

# 0.05 is below range_min; inf/nan are non-finite.
SAMPLE_RANGES = [0.05, 0.3, 0.42, 0.5, 0.7, 0.82, 0.9, math.inf, math.nan]


def make_scan(ranges=SAMPLE_RANGES, range_min=0.1, range_max=10.0):
    msg = LaserScan()
    msg.header.frame_id = 'laser'
    msg.range_min = range_min
    msg.range_max = range_max
    msg.ranges = [float(r) for r in ranges]
    return msg


def unique_namespace(prefix='sw2_test'):
    return f'/{prefix}_{os.getpid()}_{uuid.uuid4().hex[:6]}'


class Probe:
    """A best-effort LaserScan publisher and near_count subscriber for one namespace."""

    def __init__(self, node, executor, namespace):
        self.node = node
        self.executor = executor
        self.received = []
        best_effort = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                                 history=HistoryPolicy.KEEP_LAST)
        self.pub = node.create_publisher(LaserScan, f'{namespace}/scan', best_effort)
        self.sub = node.create_subscription(
            Int32, f'{namespace}/near_count', lambda m: self.received.append(m.data), 10)

    def spin_until(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            self.executor.spin_once(timeout_sec=0.05)
        return predicate()

    def exchange(self, scan, timeout=20.0):
        """Publish scan until one near_count reply arrives; return its value."""
        assert self.spin_until(
            lambda: self.pub.get_subscription_count() > 0 and self.sub.get_publisher_count() > 0,
            timeout), 'scan_watch_v2 endpoints were not discovered'
        self.received.clear()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self.received:
            self.pub.publish(scan)
            self.spin_until(lambda: bool(self.received), 0.3)
        assert self.received, 'no near_count reply'
        return self.received[0]

    def destroy(self):
        self.node.destroy_publisher(self.pub)
        self.node.destroy_subscription(self.sub)


@pytest.fixture
def ros():
    context = rclpy.Context()
    rclpy.init(context=context)
    executor = SingleThreadedExecutor(context=context)
    node = rclpy.create_node(f'scan_watch_v2_probe_{uuid.uuid4().hex[:6]}', context=context)
    executor.add_node(node)
    try:
        yield node, executor, context
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown(context=context)
