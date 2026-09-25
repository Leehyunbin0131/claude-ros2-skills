import math

import pytest
from rclpy.parameter import Parameter
from rclpy.qos import ReliabilityPolicy

from conftest import Probe, make_scan, unique_namespace
from scan_watch_v2.node import ScanWatch


def start_watch(ros, namespace, **params):
    node, executor, context = ros
    watch = ScanWatch(
        context=context, namespace=namespace,
        parameter_overrides=[Parameter(k, value=v) for k, v in params.items()])
    executor.add_node(watch)
    return watch


def test_relative_topics_are_namespaced_and_best_effort(ros):
    ns = unique_namespace()
    watch = start_watch(ros, ns)
    assert watch.get_namespace() == ns
    assert watch.sub.topic_name == f'{ns}/scan'
    assert watch.pub.topic_name == f'{ns}/near_count'
    node = ros[0]
    info = [i for i in node.get_subscriptions_info_by_topic(f'{ns}/scan')]
    assert info and info[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
    watch.destroy_node()


def test_default_limit_callback_over_best_effort(ros):
    ns = unique_namespace()
    watch = start_watch(ros, ns)
    assert watch.get_parameter('limit').value == pytest.approx(0.42)
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 2
    assert probe.exchange(make_scan([])) == 0
    probe.destroy()
    watch.destroy_node()


def test_limit_override_and_runtime_update(ros):
    ns = unique_namespace()
    watch = start_watch(ros, ns, limit=0.82)
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 5
    assert watch.set_parameters([Parameter('limit', value=0.5)])[0].successful
    assert probe.exchange(make_scan()) == 3
    # Integer limits are accepted; non-numeric and non-finite ones are rejected.
    assert watch.set_parameters([Parameter('limit', value=1)])[0].successful
    assert probe.exchange(make_scan()) == 6
    assert not watch.set_parameters([Parameter('limit', value='far')])[0].successful
    assert not watch.set_parameters([Parameter('limit', value=math.nan)])[0].successful
    assert probe.exchange(make_scan()) == 6
    probe.destroy()
    watch.destroy_node()


def test_invalid_initial_limit_is_rejected(ros):
    with pytest.raises(ValueError):
        start_watch(ros, unique_namespace(), limit='far')
