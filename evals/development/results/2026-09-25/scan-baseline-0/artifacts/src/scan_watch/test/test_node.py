import math

import pytest
import rclpy
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan

from scan_watch.node import ScanWatch


@pytest.fixture
def node():
    rclpy.init()
    node = ScanWatch()
    published = []
    node.pub.publish = published.append
    node.published = published
    yield node
    node.destroy_node()
    rclpy.shutdown()


def test_topics_are_relative(node):
    assert node.sub.topic_name == '/scan'
    assert node.pub.topic_name == '/near_count'


def test_callback_publishes_count(node):
    node.receive(LaserScan(range_min=0.1, range_max=2.0,
                           ranges=[0.05, 0.1, 0.4, 0.5, math.inf, math.nan]))
    node.receive(LaserScan())
    assert [m.data for m in node.published] == [2, 0]


def test_limit_accepts_int_and_float(node):
    assert node.limit == pytest.approx(0.4)
    assert node.set_parameters([Parameter('limit', value=1)])[0].successful
    assert node.limit == 1.0
    assert node.set_parameters([Parameter('limit', value=0.8)])[0].successful
    assert node.limit == 0.8


@pytest.mark.parametrize('bad', ['near', True, math.nan])
def test_limit_rejects_non_numbers(node, bad):
    assert not node.set_parameters([Parameter('limit', value=bad)])[0].successful
    assert node.limit == pytest.approx(0.4)
