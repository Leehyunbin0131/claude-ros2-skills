#!/usr/bin/env python3
"""Build/test real temporary packages; never calls a model or robot.

Requires colcon-common-extensions, pytest, CMake and a C++ compiler. Demonstrates
the development skill's evidence gate, not an agent performance comparison.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'skills/ros2-development/scripts/check_test_results.py'
EVIDENCE = ROOT / 'skills/ros2-development/scripts/evidence.py'


@unittest.skipUnless(shutil.which('colcon') and shutil.which('cmake'),
                     'requires colcon-common-extensions and CMake')
class ColconWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='ros2-development-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.workspace = Path(cls.temp.name)
        cls.env = {**os.environ, 'COLCON_HOME': str(cls.workspace/'colcon-home'),
                   'COLCON_DEFAULTS_FILE': str(cls.workspace/'no-defaults.yaml')}
        (cls.workspace/'no-defaults.yaml').write_text('{}\n')
        for name, build_type in [('passing_py', 'ament_python'), ('failing_py', 'ament_python'),
                                 ('skipped_py', 'ament_python'), ('passing_cpp', 'cmake'),
                                 ('empty_cpp', 'cmake')]:
            pkg = cls.workspace/'src'/name
            pkg.mkdir(parents=True)
            (pkg/'package.xml').write_text(f'''<package format="3">
<name>{name}</name><version>0.0.0</version><description>Test fixture</description>
<maintainer email="test@example.com">Test</maintainer><license>Apache-2.0</license>
<export><build_type>{build_type}</build_type></export></package>''')
            if build_type == 'ament_python':
                (pkg/name).mkdir()
                (pkg/name/'__init__.py').write_text('def add(a, b):\n    return a + b\n')
                (pkg/'setup.py').write_text(f'''from setuptools import setup
setup(name='{name}', version='0.0.0', packages=['{name}'])
''')
                (pkg/'test').mkdir()
                expectation = 99 if name == 'failing_py' else 3
                decorator = "import pytest\n@pytest.mark.skip(reason='fixture')\n" if name == 'skipped_py' else ''
                (pkg/'test/test_add.py').write_text(f'''from {name} import add
{decorator}def test_add():
    assert add(1, 2) == {expectation}
''')
            else:
                (pkg/'main.cpp').write_text('int main() { return 0; }\n')
                tests = 'enable_testing()\nadd_test(NAME runs COMMAND fixture)\n' if name == 'passing_cpp' else ''
                (pkg/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.16)
project({name} LANGUAGES CXX)
add_executable(fixture main.cpp)
install(TARGETS fixture DESTINATION lib/${{PROJECT_NAME}})
{tests}''')
        result = cls.run_command(['colcon', 'build', '--event-handlers', 'console_direct+'])
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    @classmethod
    def run_command(cls, command):
        return subprocess.run(command, cwd=cls.workspace, env=cls.env,
                              text=True, capture_output=True, timeout=120)

    def test_pass_fail_empty_skipped_and_stale(self):
        for package, expected in [('passing_py', 0), ('failing_py', 1), ('skipped_py', 2),
                                  ('passing_cpp', 0), ('empty_cpp', 2)]:
            with self.subTest(package=package):
                results = self.workspace/('results-' + package)
                results.mkdir()
                run = self.run_command(['colcon', 'test', '--packages-select', package,
                    '--return-code-on-test-failure', '--python-testing', 'pytest',
                    '--test-result-base', str(results)])
                self.assertEqual(run.returncode, 1 if expected == 1 else 0,
                                 run.stdout + run.stderr)
                check = self.run_command([sys.executable, str(CHECK), str(results),
                                          '--packages', package])
                self.assertEqual(check.returncode, expected, check.stdout + check.stderr)
                if package in ('passing_py', 'passing_cpp'):
                    test_name = 'test_add' if package == 'passing_py' else 'runs'
                    named = self.run_command([sys.executable, str(CHECK), str(results),
                        '--packages', package, '--require-test', package+'::'+test_name])
                    self.assertEqual(named.returncode, 0, named.stdout + named.stderr)
                    absent = self.run_command([sys.executable, str(CHECK), str(results),
                        '--packages', package, '--require-test', package+'::missing_behavior'])
                    self.assertEqual(absent.returncode, 2, absent.stdout + absent.stderr)
                if package == 'empty_cpp':
                    # The raw command succeeds despite having executed no test.
                    raw = self.run_command(['colcon', 'test-result', '--test-result-base', str(results)])
                    self.assertEqual(raw.returncode, 0)
                    self.assertIn('0 tests', raw.stdout)
        # A previous successful report cannot satisfy a fresh run's directory.
        fresh = self.workspace/'new-results'
        fresh.mkdir()
        check = self.run_command([sys.executable, str(CHECK), str(fresh),
                                  '--packages', 'passing_py'])
        self.assertEqual(check.returncode, 2, check.stdout + check.stderr)

    def test_record_consistency_is_separate_from_real_test_coverage(self):
        for package, coverage_code in [('passing_cpp', 0), ('empty_cpp', 2)]:
            with self.subTest(package=package):
                record = self.workspace / ('evidence-' + package)
                results = self.workspace / ('evidence-results-' + package)
                command = ['colcon', 'test', '--packages-select', package,
                           '--return-code-on-test-failure', '--test-result-base', str(results)]
                start = self.run_command([sys.executable, str(EVIDENCE), 'begin',
                    '--workspace', str(self.workspace), '--output', str(record),
                    '--scope', package + ' test invocation', '--command', ' '.join(command),
                    '--watch', 'src', '--watch', f'install/{package}/lib/{package}/fixture'])
                self.assertEqual(start.returncode, 0, start.stdout + start.stderr)
                run = self.run_command(command)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                log = self.workspace / (package + '-declared.log')
                log.write_text(run.stdout + run.stderr)
                finish = self.run_command([sys.executable, str(EVIDENCE), 'finish', str(record),
                    '--exit-code', str(run.returncode), '--log', str(log)])
                self.assertEqual(finish.returncode, 0, finish.stdout + finish.stderr)
                self.assertEqual(json.loads(finish.stdout)['record_status'], 'consistent')
                coverage = self.run_command([sys.executable, str(CHECK), str(results), '--packages', package])
                self.assertEqual(coverage.returncode, coverage_code, coverage.stdout + coverage.stderr)
                # Same source code, different installed artifact: the record must change.
                executable = self.workspace / f'install/{package}/lib/{package}/fixture'
                original = executable.read_bytes()
                try:
                    executable.write_bytes(original + b'changed installed artifact')
                    inspection = self.run_command([sys.executable, str(EVIDENCE), 'inspect', str(record)])
                    self.assertEqual(inspection.returncode, 1, inspection.stdout + inspection.stderr)
                    self.assertTrue(any('install/' in p for p in json.loads(inspection.stdout)['observed']['changes']))
                finally:
                    executable.write_bytes(original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
