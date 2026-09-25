"""Launch the installed monitor.launch.py and check real near_count output."""
import math
import os
import time
import unittest

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing
import launch_testing.actions
import pytest
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32

NAMESPACE = f'scan_watch_test_{os.getpid()}'
# Counted per limit (range_min=0.1, range_max=2.0):
#   0.4 -> 0.1 0.3 0.4    0.8 -> + 0.5 0.8    1 -> + 1.0
RANGES = [0.05, 0.1, 0.3, 0.4, 0.5, 0.8, 1.0, 2.0, 2.5, math.inf, math.nan, -math.inf]


@pytest.mark.launch_test
@launch_testing.parametrize('limit_arg, expected', [
    (None, 3),     # limit:= omitted -> config/monitor.yaml (0.4)
    ('0.8', 5),    # explicit override
    ('1', 6),      # integer-looking override is accepted
])
def generate_test_description(limit_arg, expected):
    launch_args = {'namespace': NAMESPACE}
    if limit_arg is not None:
        launch_args['limit'] = limit_arg
    monitor = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('scan_watch'), 'launch', 'monitor.launch.py')),
        launch_arguments=launch_args.items())
    return LaunchDescription([monitor, launch_testing.actions.ReadyToTest()])


class TestMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node('scan_watch_tester')

    def tearDown(self):
        self.node.destroy_node()

    def _count_for_scan(self, reliability, timeout=15.0):
        received = []
        self.node.create_subscription(
            Int32, f'/{NAMESPACE}/near_count', lambda m: received.append(m.data), 10)
        pub = self.node.create_publisher(
            LaserScan, f'/{NAMESPACE}/scan', QoSProfile(depth=5, reliability=reliability))
        scan = LaserScan(range_min=0.1, range_max=2.0, ranges=RANGES)
        deadline = time.monotonic() + timeout
        # Republish until discovery completes and a result comes back.
        while not received and time.monotonic() < deadline:
            pub.publish(scan)
            rclpy.spin_once(self.node, timeout_sec=0.2)
        self.assertTrue(received, 'no near_count received')
        return received[-1]

    def test_node_is_namespaced(self):
        deadline = time.monotonic() + 10.0
        names = []
        while time.monotonic() < deadline:
            names = self.node.get_node_names_and_namespaces()
            if ('scan_watch', f'/{NAMESPACE}') in names:
                break
            time.sleep(0.2)
        self.assertIn(('scan_watch', f'/{NAMESPACE}'), names)

    def test_best_effort_publisher(self, expected):
        self.assertEqual(self._count_for_scan(ReliabilityPolicy.BEST_EFFORT), expected)

    def test_reliable_publisher(self, expected):
        self.assertEqual(self._count_for_scan(ReliabilityPolicy.RELIABLE), expected)


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):

    def test_exit_code(self, proc_info):
        launch_testing.asserts.assertExitCodes(
            proc_info, allowable_exit_codes=[0, -2, -15])
