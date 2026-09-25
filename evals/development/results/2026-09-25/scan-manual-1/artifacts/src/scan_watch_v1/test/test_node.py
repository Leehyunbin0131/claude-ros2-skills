import math
import os
import sys
import uuid

import pytest
from rclpy.exceptions import InvalidParameterValueException
from rclpy.parameter import Parameter

from scan_watch_v1.node import ScanWatch

sys.path.insert(0, os.path.dirname(__file__))
from probe import Probe, exchange, make_scan, new_executor  # noqa: E402


def _ns():
    return 'test_node_' + uuid.uuid4().hex[:8]


def test_callback_counts_with_best_effort_publisher(ros_context):
    ns = _ns()
    node = ScanWatch(context=ros_context, namespace=ns,
                     parameter_overrides=[Parameter('limit', value=0.81)])
    probe = Probe(ns, ros_context)
    ex = new_executor(ros_context, node, probe)
    try:
        assert node.get_fully_qualified_name() == f'/{ns}/scan_watch_v1'
        scan = make_scan([0.05, 0.2, 0.81, 0.82, math.inf, math.nan, 11.0],
                         range_min=0.1, range_max=10.0)
        # 0.2 and 0.81 (at limit); 0.05 < range_min, 0.82 > limit, non-finite, > range_max
        assert exchange(ex, probe, scan) == 2
        assert exchange(ex, probe, make_scan([])) == 0
        # A runtime parameter change takes effect on the next scan.
        node.set_parameters([Parameter('limit', value=0.1)])
        assert exchange(ex, probe, make_scan([0.1, 0.2])) == 1
    finally:
        ex.shutdown()
        probe.destroy_node()
        node.destroy_node()


def test_default_limit_is_0_41(ros_context):
    node = ScanWatch(context=ros_context, namespace=_ns())
    try:
        assert node.limit() == pytest.approx(0.41)
    finally:
        node.destroy_node()


def test_integer_limit_accepted(ros_context):
    node = ScanWatch(context=ros_context, namespace=_ns(),
                     parameter_overrides=[Parameter('limit', value=1)])
    try:
        assert node.limit() == 1.0
    finally:
        node.destroy_node()


@pytest.mark.parametrize('bad', ['near', math.nan, math.inf])
def test_invalid_limit_rejected(ros_context, bad):
    with pytest.raises(InvalidParameterValueException):
        ScanWatch(context=ros_context, namespace=_ns(),
                  parameter_overrides=[Parameter('limit', value=bad)])


def test_invalid_runtime_limit_rejected(ros_context):
    node = ScanWatch(context=ros_context, namespace=_ns())
    try:
        result = node.set_parameters([Parameter('limit', value='far')])[0]
        assert not result.successful
        assert node.limit() == pytest.approx(0.41)
    finally:
        node.destroy_node()
