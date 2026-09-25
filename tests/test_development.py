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
    def test_required_names_suffix_parameters_and_missing(self):
        cases = {'pkg.test.test_math.test_ratio[forward]': ['passed'],
                 'pkg.test.test_math.test_ratio[reverse]': ['skipped'],
                 'pkg.test.test_style.test_flake8': ['passed']}
        for selector in ('test_ratio', 'test_math.test_ratio',
                         'test_ratio[forward]'):
            self.assertEqual(evidence.required_verdict(cases, selector)[0], 0)
        for selector in ('test_ratio[reverse]', 'test_missing', 'ratio'):
            self.assertEqual(evidence.required_verdict(cases, selector)[0], 2)
        cases['pkg.test.test_math.test_ratio[reverse]'] = ['failed']
        self.assertEqual(evidence.required_verdict(cases, 'test_ratio')[0], 1)

    def test_lint_pass_does_not_satisfy_required_behavior(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            base = Path(d)
            (base/'pkg').mkdir()
            (base/'pkg/result.xml').write_text('''<testsuite tests="2" failures="0" skipped="1">
                <testcase classname="test.test_style" name="test_flake8"/>
                <testcase classname="test.test_logic" name="test_behavior"><skipped/></testcase>
                </testsuite>''')
            def run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0,
                    'Summary: 2 tests, 0 errors, 0 failures, 1 skipped', '')
            self.assertEqual(evidence.check(base, ['pkg'], run=run), 0)
            self.assertEqual(evidence.check(base, ['pkg'],
                required=[('pkg', 'test_behavior')], run=run), 2)

    def test_missing_runner_result_and_real_errors(self):
        for sentinel, element, expected in [('pytest.missing_result', 'failure', 2),
                                           ('behavior.xunit.missing_result', 'error', 1),
                                           ('crash_gtest.gtest.missing_result', 'error', 1)]:
            with self.subTest(sentinel=sentinel), tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
                base = Path(d)
                (base/'pkg').mkdir()
                report = base/'pkg/result.xml'
                report.write_text(f'<testsuite><testcase classname="pkg" name="{sentinel}"><{element}/></testcase></testsuite>')
                def run(command, **kwargs):
                    return subprocess.CompletedProcess(command, 1,
                        'Summary: 1 test, 1 error, 0 failures, 0 skipped', '')
                self.assertEqual(evidence.check(base, ['pkg'], run=run), expected)
                report.write_text('<testsuite><testcase name="test_behavior"><error/></testcase></testsuite>')
                self.assertEqual(evidence.check(base, ['pkg'], run=run), 1)

    def test_ctest_uses_current_tag_and_exposes_test_names(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            current = base/'Testing/current'
            old = base/'Testing/old'
            current.mkdir(parents=True)
            old.mkdir()
            (base/'Testing/TAG').write_text('current\n')
            (current/'Test.xml').write_text('<Site><Testing><Test Status="passed"><Name>behavior</Name></Test></Testing></Site>')
            (old/'Test.xml').write_text('<Site><Testing><Test Status="failed"><Name>behavior</Name></Test></Testing></Site>')
            cases, missing, failed = evidence.test_cases(base)
            self.assertEqual(cases, {'behavior': ['passed']})
            self.assertFalse(missing or failed)
            self.assertEqual(evidence.required_verdict(cases, 'behavior')[0], 0)

    def test_ctest_failure_is_not_cleared_by_missing_python_result(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            current = base/'Testing/current'
            current.mkdir(parents=True)
            (base/'Testing/TAG').write_text('current\n')
            (base/'runner.xml').write_text('<testsuite><testcase name="pytest.missing_result"><error/></testcase></testsuite>')
            (current/'Test.xml').write_text('<Site><Testing><Test Status="failed"><Name>runner</Name></Test></Testing></Site>')
            self.assertEqual(evidence.test_cases(base)[1:], (True, True))
            (current/'Test.xml').write_text('<Site><Testing><Test Status="failed"><Name>other_behavior</Name></Test></Testing></Site>')
            self.assertEqual(evidence.test_cases(base)[1:], (True, True))

    def test_ament_wrapper_resolves_inner_report_and_ignores_stale_when_notrun(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            base = Path(d)/'fresh'
            current = base/'pkg/Testing/current'
            current.mkdir(parents=True)
            (current.parent/'TAG').write_text('current\n')
            inner = Path(d)/'build-results.xml'
            inner.write_text('<testsuite><testcase name="test_behavior"><skipped/></testcase></testsuite>')
            report = current/'Test.xml'
            report.write_text(f'''<Site><Testing><Test Status="passed"><Name>behavior_wrapper</Name>
                <FullCommandLine>/usr/bin/python3 /opt/ros/jazzy/share/ament_cmake_test/cmake/run_test.py "{inner}"</FullCommandLine>
                </Test></Testing></Site>''')
            def run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0,
                    'Summary: 1 test, 0 errors, 0 failures, 0 skipped', '')
            self.assertEqual(evidence.check(base, ['pkg'], run=run), 2)
            self.assertEqual(evidence.check(base, ['pkg'], required=[('pkg', 'behavior_wrapper')], run=run), 2)
            inner.write_text('<testsuite><testcase name="test_behavior"/></testsuite>')
            self.assertEqual(evidence.check(base, ['pkg'], required=[('pkg', 'behavior_wrapper')], run=run), 0)
            report.write_text(report.read_text().replace('Status="passed"', 'Status="notrun"'))
            cases, _, _ = evidence.test_cases(base/'pkg')
            self.assertEqual(cases, {'behavior_wrapper': ['skipped']})

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
