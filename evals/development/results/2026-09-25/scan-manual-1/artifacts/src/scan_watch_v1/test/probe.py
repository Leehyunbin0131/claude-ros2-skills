"""Test helper: a best-effort LaserScan publisher plus a near_count subscriber."""
import time

from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

BEST_EFFORT = QoSProfile(depth=5, history=HistoryPolicy.KEEP_LAST,
                         reliability=ReliabilityPolicy.BEST_EFFORT)


def make_scan(ranges, range_min=0.1, range_max=10.0):
    msg = LaserScan()
    msg.header.frame_id = 'laser'
    msg.range_min = range_min
    msg.range_max = range_max
    msg.ranges = [float(r) for r in ranges]
    return msg


class Probe(Node):
    def __init__(self, namespace, context):
        super().__init__('scan_probe', namespace=namespace, context=context)
        self.scan_pub = self.create_publisher(LaserScan, 'scan', BEST_EFFORT)
        self.received = []
        self.create_subscription(Int32, 'near_count', lambda m: self.received.append(m.data), 10)


def exchange(executor, probe, scan, timeout=10.0):
    """Publish `scan` repeatedly until one near_count arrives; return its value."""
    probe.received.clear()
    deadline = time.monotonic() + timeout
    next_pub = 0.0
    while time.monotonic() < deadline:
        now = time.monotonic()
        # Best-effort: republish until discovery completes and a result arrives.
        if now >= next_pub:
            probe.scan_pub.publish(scan)
            next_pub = now + 0.2
        executor.spin_once(timeout_sec=0.05)
        if probe.received:
            return probe.received[0]
    raise TimeoutError('no near_count received')


def new_executor(context, *nodes):
    executor = SingleThreadedExecutor(context=context)
    for n in nodes:
        executor.add_node(n)
    return executor
