#!/usr/bin/env python3
"""Test the development skill's evidence gate without ROS or colcon."""
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('test_evidence', ROOT /
    'skills/ros2-development/scripts/check_test_results.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class TestEvidence(unittest.TestCase):
    def test_passing_summary(self):
        self.assertEqual(evidence.verdict(0, 'Summary: 3 tests, 0 errors, 0 failures, 1 skipped')[0], 0)

    def test_zero_or_all_skipped_is_not_success(self):
        for line in ('Summary: 0 tests, 0 errors, 0 failures, 0 skipped',
                     'Summary: 1 test, 0 errors, 0 failures, 1 skipped'):
            self.assertEqual(evidence.verdict(0, line)[0], 2)

    def test_real_failure_wins_over_passed_tests(self):
        self.assertEqual(evidence.verdict(1, 'Summary: 8 tests, 0 errors, 1 failure, 0 skipped')[0], 1)

    def test_missing_or_invalid_evidence(self):
        for code, stdout, stderr in [(0, '', ''), (2, '', 'invalid path'),
                (0, 'Summary: 2 tests, 0 errors, 0 failures, 0 skipped', 'parser failed'),
                (1, 'Summary: 2 tests, 0 errors, 0 failures, 0 skipped', ''),
                (0, 'Summary: 1 test, 0 errors, 0 failures, 2 skipped', '')]:
            self.assertEqual(evidence.verdict(code, stdout, stderr)[0], 2)

    def test_each_requested_package_needs_evidence(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            base = Path(d)
            (base/'present').mkdir()
            def run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0,
                    'Summary: 1 test, 0 errors, 0 failures, 0 skipped', '')
            self.assertEqual(evidence.check(base, ['present', 'missing'], run=run), 2)
            self.assertEqual(evidence.check(base, ['present'], run=run), 0)

    def test_missing_colcon_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            (Path(d)/'pkg').mkdir()
            def run(*args, **kwargs):
                raise FileNotFoundError('colcon is not installed')
            self.assertEqual(evidence.check(Path(d), ['pkg'], run=run), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
