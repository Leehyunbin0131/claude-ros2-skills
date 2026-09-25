import math
import os
import time
import uuid

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

from scan_watch_v3.node import ScanWatch

CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config', 'monitor.yaml')


@pytest.fixture
def context():
    ctx = rclpy.Context()
    rclpy.init(context=ctx)
    yield ctx
    rclpy.try_shutdown(context=ctx)


def unique_namespace():
    return f'/scan_watch_test_{uuid.uuid4().hex[:12]}'


def make_scan(ranges, range_min=0.1, range_max=10.0):
    msg = LaserScan()
    msg.range_min = range_min
    msg.range_max = range_max
    msg.ranges = ranges
    return msg


def exchange(context, watch, scans, reliability, timeout=10.0):
    """Publish scans to the node's `scan` topic and collect its near_count output."""
    ns = watch.get_namespace()
    probe = rclpy.create_node('probe', namespace=ns, context=context)
    received = []
    probe.create_subscription(Int32, 'near_count', lambda m: received.append(m.data), 10)
    pub = probe.create_publisher(
        LaserScan, 'scan', QoSProfile(depth=10, reliability=reliability))
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(watch)
    executor.add_node(probe)
    try:
        deadline = time.monotonic() + timeout
        # Wait until both directions are matched before publishing.
        while time.monotonic() < deadline and (
                pub.get_subscription_count() == 0
                or watch.pub.get_subscription_count() == 0):
            executor.spin_once(timeout_sec=0.05)
        assert pub.get_subscription_count() == 1, 'node did not match the scan publisher'
        for scan in scans:
            pub.publish(scan)
            end = time.monotonic() + 2.0
            count = len(received)
            while time.monotonic() < end and len(received) == count:
                executor.spin_once(timeout_sec=0.05)
        return received
    finally:
        executor.shutdown()
        probe.destroy_node()


def test_default_limit(context):
    watch = ScanWatch(context=context)
    try:
        assert watch.limit() == pytest.approx(0.43)
    finally:
        watch.destroy_node()


def test_yaml_applies_under_namespace(context):
    watch = ScanWatch(
        context=context, namespace=unique_namespace(),
        cli_args=['--ros-args', '--params-file', CONFIG,
                  '-p', 'limit:=0.83'])
    try:
        # Later override wins, proving the YAML is loaded first and can be overridden.
        assert watch.limit() == pytest.approx(0.83)
    finally:
        watch.destroy_node()
    watch = ScanWatch(
        context=context, namespace=unique_namespace(),
        cli_args=['--ros-args', '--params-file', CONFIG])
    try:
        assert watch.get_fully_qualified_name().endswith('/scan_watch_v3')
        assert watch.limit() == pytest.approx(0.43)
    finally:
        watch.destroy_node()


def test_integer_limit_is_accepted_and_invalid_rejected(context):
    watch = ScanWatch(context=context, parameter_overrides=[Parameter('limit', value=1)])
    try:
        assert watch.limit() == 1.0
        result = watch.set_parameters([Parameter('limit', value='near')])[0]
        assert not result.successful
        result = watch.set_parameters([Parameter('limit', value=math.nan)])[0]
        assert not result.successful
        assert watch.set_parameters([Parameter('limit', value=0.5)])[0].successful
        assert watch.limit() == 0.5
    finally:
        watch.destroy_node()


def test_invalid_initial_limit_is_rejected(context):
    with pytest.raises(ValueError):
        ScanWatch(context=context, parameter_overrides=[Parameter('limit', value='x')])


def test_topics_are_relative_to_namespace(context):
    ns = unique_namespace()
    watch = ScanWatch(context=context, namespace=ns)
    try:
        assert watch.sub.topic_name == f'{ns}/scan'
        assert watch.pub.topic_name == f'{ns}/near_count'
    finally:
        watch.destroy_node()


@pytest.mark.parametrize('reliability', [
    ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE])
def test_callback_counts_scans_over_dds(context, reliability):
    watch = ScanWatch(
        context=context, namespace=unique_namespace(),
        parameter_overrides=[Parameter('limit', value=0.83)])
    try:
        scans = [
            make_scan([0.05, 0.2, 0.83, 0.9, math.nan, math.inf, 0.5]),
            make_scan([]),
            make_scan([0.3, 0.4], range_min=0.35, range_max=0.39),
        ]
        received = exchange(context, watch, scans, reliability)
        assert received == [3, 0, 0]
    finally:
        watch.destroy_node()
