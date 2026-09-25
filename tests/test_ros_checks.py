#!/usr/bin/env python3
"""Synthetic Jazzy integration tests; no hardware or motion commands.

source /opt/ros/jazzy/setup.bash
python3 tests/test_ros_checks.py
"""
import os
import math
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
import unittest
import uuid

# Separate graph, localhost discovery, unique topics. No ros2 daemon is used.
# Positive cases allow discovery retransmission in a cold CI container. The
# short missing-data tests below verify deadlines separately; this suite does
# not assert sub-second middleware discovery performance.
os.environ['ROS_DOMAIN_ID'] = '173'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
import rclpy
from rclpy.duration import Duration
from rclpy.qos import (QoSProfile, ReliabilityPolicy, DurabilityPolicy,
                      LivelinessPolicy, qos_check_compatible, qos_profile_sensor_data)
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/ros2-troubleshooting/scripts'
sys.path.insert(0, str(SCRIPTS))
from check_qos_compat import compatibility_verdict


class RosChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('check_regression_' + uuid.uuid4().hex[:8])

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def command(self, script, args, publish=None, limit=15):
        proc = subprocess.Popen([sys.executable, '-u', str(SCRIPTS/script), *args],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        output = []
        pending = queue.Queue()
        def read():
            for line in proc.stdout:
                pending.put(line.rstrip())
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        motion_at = None
        deadline = time.monotonic() + limit
        try:
            while proc.poll() is None and time.monotonic() < deadline:
                while not pending.empty():
                    line = pending.get_nowait()
                    output.append(line)
                    if 'non-interactive: waiting' in line:
                        motion_at = time.monotonic()
                if publish:
                    publish(None if motion_at is None else time.monotonic()-motion_at)
                rclpy.spin_once(self.node, timeout_sec=0.005)
                time.sleep(0.025)
            self.assertIsNotNone(proc.poll(), f'check exceeded {limit}s: {output}')
            reader.join(timeout=1)
            while not pending.empty():
                output.append(pending.get_nowait())
            text = '\n'.join(output)
            self.assertNotIn('Traceback', text)
            return proc.returncode, text
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            reader.join(timeout=1)
            proc.stdout.close()

    def imu(self, values, expected, unavailable=False):
        topic = '/regression/imu_' + uuid.uuid4().hex
        pub = self.node.create_publisher(Imu, topic, qos_profile_sensor_data)
        def publish(_):
            msg = Imu()
            msg.header.frame_id = 'imu_link'
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = values
            if unavailable:
                msg.linear_acceleration_covariance[0] = -1.0
            pub.publish(msg)
        try:
            code, text = self.command('check_imu_gravity.py',
                                      ['--topic', topic, '--samples', '4', '--timeout', '6',
                                       '--assume-aligned'], publish)
            self.assertEqual(code, expected, text)
            if unavailable:
                self.assertIn('marks acceleration unavailable', text)
            elif any(not math.isfinite(value) for value in values):
                self.assertIn('non-finite', text)
        finally:
            self.node.destroy_publisher(pub)

    def test_imu_valid_and_flipped(self):
        self.imu((0.0, 0.0, 9.81), 0)
        self.imu((0.0, 0.0, -9.81), 1)

    def test_imu_invalid_and_unavailable(self):
        self.imu((0.0, float('nan'), 9.81), 2)
        self.imu((0.0, 0.0, 9.81), 2, unavailable=True)

    def test_imu_uses_declared_mount(self):
        topic = '/regression/imu_tf_' + uuid.uuid4().hex
        frame = 'imu_' + uuid.uuid4().hex
        pub = self.node.create_publisher(Imu, topic, qos_profile_sensor_data)
        broadcaster = StaticTransformBroadcaster(self.node)
        transform = TransformStamped()
        transform.header.frame_id = 'regression_base'
        transform.child_frame_id = frame
        transform.transform.rotation.x = 1.0
        transform.transform.rotation.w = 0.0
        broadcaster.sendTransform(transform)
        def publish(_):
            msg = Imu()
            msg.header.frame_id = frame
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.linear_acceleration.z = -9.81
            pub.publish(msg)
        try:
            code, text = self.command('check_imu_gravity.py',
                                      ['--topic', topic, '--base', 'regression_base',
                                       '--samples', '4', '--timeout', '6'], publish)
            self.assertEqual(code, 0, text)
            code, text = self.command('check_imu_gravity.py',
                                      ['--topic', topic, '--base', 'missing_'+frame,
                                       '--samples', '4', '--timeout', '6'], publish)
            self.assertEqual(code, 2, text)
            self.assertIn('TF', text)
        finally:
            self.node.destroy_publisher(pub)
            self.node.destroy_publisher(broadcaster.pub_tf)

    def test_eval_imu_fixture_exposes_declared_mount_mismatch(self):
        harness = SCRIPTS.parents[2] / 'evals/harness'
        sys.path.insert(0, str(harness))
        from fake_imu_pub import FakeImu
        topic = '/regression/fixture_' + uuid.uuid4().hex
        fixture = FakeImu(topic, 50.0)
        try:
            code, text = self.command('check_imu_gravity.py',
                                      ['--topic', topic, '--samples', '4', '--timeout', '6'],
                                      lambda _: fixture.tick())
            self.assertEqual(code, 1, text)
            self.assertIn('FAIL', text)
        finally:
            fixture.destroy_node()

    def odom(self, case, expected):
        topic = '/regression/odom_' + uuid.uuid4().hex
        pub = self.node.create_publisher(Odometry, topic, qos_profile_sensor_data)
        def publish(elapsed):
            if case == 'stopped' and elapsed is not None:
                return
            msg = Odometry()
            msg.header.frame_id = 'odom'
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.child_frame_id = 'base_link'
            msg.pose.pose.orientation.w = 1.0
            if elapsed is not None:
                if case in ('forward', 'frame_change'):
                    msg.pose.pose.position.x = 1.0
                elif case == 'backward':
                    msg.pose.pose.position.x = -1.0
                elif case == 'stale_queue' and elapsed > 0.75:
                    msg.pose.pose.position.x = 1.0
                if case == 'frame_change':
                    msg.header.frame_id = 'map'
            if case == 'invalid':
                msg.pose.pose.orientation.w = 0.0
            pub.publish(msg)
        try:
            code, text = self.command('check_odom_direction.py',
                                      ['--topic', topic, '--timeout', '6', '--wait-secs', '0.8'], publish)
            self.assertEqual(code, expected, text)
        finally:
            self.node.destroy_publisher(pub)

    def test_odometry_directions(self):
        self.odom('forward', 0)
        self.odom('backward', 1)
        self.odom('stationary', 2)

    def test_odometry_requires_fresh_usable_pose(self):
        self.odom('stale_queue', 0)
        self.odom('stopped', 2)
        self.odom('invalid', 2)
        self.odom('frame_change', 2)

    def test_missing_data(self):
        topic = '/regression/missing_' + uuid.uuid4().hex
        for script, args in [
            ('check_imu_gravity.py', ['--topic', topic, '--timeout', '0.2']),
            ('check_odom_direction.py', ['--topic', topic, '--timeout', '0.2', '--wait-secs', '0']),
            ('check_qos_compat.py', ['--topic', topic, '--wait', '0.2']),
        ]:
            code, text = self.command(script, args)
            self.assertEqual(code, 2, text)

    def test_interrupt_cleans_up_without_shutdown_error(self):
        for script, args in [
            ('check_imu_gravity.py', ['--timeout', '20']),
            ('check_odom_direction.py', ['--timeout', '20', '--wait-secs', '0']),
            ('check_qos_compat.py', ['--topic', '/regression/cancel', '--wait', '20']),
            ('check_tf_tree.py', ['--map-frame', 'regression_missing', '--timeout', '20']),
        ]:
            proc = subprocess.Popen([sys.executable, '-u', str(SCRIPTS/script), *args],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                time.sleep(0.8)
                proc.send_signal(signal.SIGINT)
                output, _ = proc.communicate(timeout=4)
                self.assertEqual(proc.returncode, 130, output)
                self.assertNotIn('Traceback', output)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()

    def test_qos_native_policy_semantics(self):
        def profile(**kw):
            values = dict(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.VOLATILE,
                          liveliness=LivelinessPolicy.AUTOMATIC)
            values.update(kw)
            return QoSProfile(**values)
        cases = [
            (profile(), profile(), 'PASS'),
            (profile(reliability=ReliabilityPolicy.BEST_EFFORT), profile(), 'FAIL'),
            (profile(), profile(reliability=ReliabilityPolicy.BEST_EFFORT), 'PASS'),
            (profile(), profile(durability=DurabilityPolicy.TRANSIENT_LOCAL), 'FAIL'),
            (profile(), profile(liveliness=LivelinessPolicy.MANUAL_BY_TOPIC), 'FAIL'),
            # Zero is the RMW default, not a literal zero-second deadline.
            (profile(), profile(deadline=Duration(seconds=0.2)), 'FAIL'),
            (profile(deadline=Duration(seconds=0.2)), profile(), 'PASS'),
            (profile(reliability=ReliabilityPolicy.SYSTEM_DEFAULT), profile(), 'INCONCLUSIVE'),
        ]
        for pub, sub, expected in cases:
            status, reason = qos_check_compatible(pub, sub)
            self.assertEqual(compatibility_verdict(status.name), expected, reason)

    def test_qos_discovered_pairs(self):
        for compatible in (True, False):
            topic = '/regression/qos_' + uuid.uuid4().hex
            pub = self.node.create_publisher(String, topic, qos_profile_sensor_data)
            sub = self.node.create_subscription(String, topic, lambda _: None,
                                                qos_profile_sensor_data if compatible else 10)
            try:
                code, text = self.command('check_qos_compat.py', ['--topic', topic, '--wait', '6'])
                self.assertEqual(code, 0 if compatible else 1, text)
            finally:
                self.node.destroy_subscription(sub)
                self.node.destroy_publisher(pub)

    def test_tf_resolved_and_missing(self):
        frame = 'sensor_' + uuid.uuid4().hex
        msg = TransformStamped()
        msg.header.frame_id = 'regression_base'
        msg.child_frame_id = frame
        msg.transform.rotation.x = 1.0  # an upside-down mounting is a warning
        msg.transform.rotation.w = 0.0
        broadcaster = StaticTransformBroadcaster(self.node)
        broadcaster.sendTransform(msg)
        try:
            code, text = self.command('check_tf_tree.py',
                                      ['--base', msg.header.frame_id, '--sensors', frame,
                                       '--no-global', '--timeout', '6'])
            self.assertEqual(code, 0, text)
            self.assertIn('UPSIDE-DOWN', text)
            code, text = self.command('check_tf_tree.py',
                                      ['--base', msg.header.frame_id, '--sensors', 'missing_'+frame,
                                       '--no-global', '--timeout', '0.2'])
            self.assertEqual(code, 1, text)
        finally:
            self.node.destroy_publisher(broadcaster.pub_tf)

    def test_tf_empty_graph_is_inconclusive(self):
        # Separate domain: this test class may have published static TF already.
        result = subprocess.run([sys.executable, str(SCRIPTS/'check_tf_tree.py'),
            '--no-global', '--sensors', 'missing_sensor', '--timeout', '0.2'],
            env={**os.environ, 'ROS_DOMAIN_ID': '174'}, capture_output=True,
            text=True, timeout=5)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('No TF frames received', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
