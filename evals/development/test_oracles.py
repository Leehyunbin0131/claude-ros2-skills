#!/usr/bin/env python3
"""Positive/negative controls for prospective release acceptance. No model calls."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from fixtures import create
from grade import grade_scan, grade_tests, passed, stop
import imu_scene


SEED = int(os.environ.get('ROS2_ACCEPTANCE_SEED', '0'))


class Oracles(unittest.TestCase):
    def test_scan_positive_and_negative_controls(self):
        os.environ['ROS_DOMAIN_ID'] = '207'
        os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
        for variant in ('good', 'best_effort_output', 'starter', 'missing_install', 'wrong_qos', 'wrong_logic', 'dead_yaml', 'wrong_namespace'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory(prefix='ros2-oracle-scan-') as d:
                root = Path(d)
                create(root/'source', 'scan', variant, seed=SEED)
                out = root/'grade'
                out.mkdir()
                result = grade_scan(root/'source', out, seed=SEED)
                self.assertEqual(passed('scan', result), variant in ('good', 'best_effort_output'), result)

    def test_test_suite_positive_and_negative_controls(self):
        for variant in ('good', 'starter', 'old_logic', 'skipped', 'vacuous'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory(prefix='ros2-oracle-tests-') as d:
                root = Path(d)
                create(root/'source', 'tests', variant, seed=SEED)
                out = root/'grade'
                out.mkdir()
                result = grade_tests(root/'source', out, seed=SEED)
                self.assertEqual(passed('tests', result), variant == 'good', result)

    def test_imu_live_statuses_and_mutation(self):
        imu_scene.configure(SEED)
        os.environ['ROS_DOMAIN_ID'] = '208'
        os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
        with tempfile.TemporaryDirectory(prefix='ros2-oracle-imu-') as d:
            root = Path(d)
            state = root/'scene.json'
            proc = subprocess.Popen([sys.executable, str(Path(imu_scene.__file__)), 'serve', '--state', str(state), '--seed', str(SEED)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            injected = None
            try:
                deadline = time.monotonic()+10
                while not state.is_file() and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(state.is_file(), 'scene did not become ready')
                observed = imu_scene.observe()
                self.assertEqual([observed[t]['status'] for t in imu_scene.TOPICS], list(imu_scene.ROLES))
                self.assertFalse(imu_scene.grade(root, state, proc.pid)['accepted'])
                (root/'diagnosis.json').write_text(json.dumps(observed))
                self.assertTrue(imu_scene.grade(root, state, proc.pid)['accepted'])
                wrong = {t: {'status': 'pass'} for t in imu_scene.TOPICS}
                (root/'diagnosis.json').write_text(json.dumps(wrong))
                self.assertFalse(imu_scene.grade(root, state, proc.pid)['accepted'])
                (root/'diagnosis.json').write_text(json.dumps(observed))
                # A fabricated missing transform fails even with the previously
                # correct answer. The publisher is owned and stopped here.
                injected = subprocess.Popen(['ros2', 'run', 'tf2_ros', 'static_transform_publisher',
                    '--frame-id', 'base_link', '--child-frame-id', imu_scene.FRAMES[imu_scene.ROLES.index('inconclusive')]],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                deadline = time.monotonic()+6
                while time.monotonic() < deadline:
                    if json.loads(state.read_text())['unexpected_topics']:
                        break
                    time.sleep(.1)
                self.assertFalse(imu_scene.grade(root, state, proc.pid)['accepted'])
            finally:
                if injected is not None:
                    stop(injected)
                stop(proc)


if __name__ == '__main__':
    unittest.main(verbosity=2)
