#!/usr/bin/env python3
"""Real ament CTest wrappers: skipped cases must not be counted as executed."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT/'skills/ros2-development/scripts/check_test_results.py'

@unittest.skipUnless(os.environ.get('ROS_DISTRO') == 'jazzy' and shutil.which('colcon'),
                     'requires sourced Jazzy, colcon and ament_cmake_pytest')
class AmentResults(unittest.TestCase):
    def test_wrapped_pass_skip_crash_and_freshness(self):
        with tempfile.TemporaryDirectory(prefix='ros2-ament-results-') as d:
            ws = Path(d)
            env = dict(os.environ, COLCON_HOME=str(ws/'colcon-home'),
                       COLCON_DEFAULTS_FILE=str(ws/'defaults.yaml'))
            (ws/'defaults.yaml').write_text('{}\n')
            def run(argv):
                return subprocess.run(argv, cwd=ws, env=env, capture_output=True, text=True, timeout=120)
            for name, body in [('wrapped_pass', 'def test_behavior():\n    assert 2 + 2 == 4\n'),
                               ('wrapped_skip', 'import pytest\n@pytest.mark.skip(reason="fixture")\ndef test_behavior():\n    assert False\n'),
                               ('wrapped_crash', 'import os\ndef test_behavior():\n    os._exit(23)\n')]:
                pkg = ws/'src'/name
                (pkg/'test').mkdir(parents=True)
                (pkg/'test/test_behavior.py').write_text(body)
                (pkg/'package.xml').write_text(f'''<package format="3"><name>{name}</name><version>0.0.0</version>
<description>Wrapper regression</description><maintainer email="test@example.com">Test</maintainer>
<license>Apache-2.0</license><buildtool_depend>ament_cmake</buildtool_depend>
<test_depend>ament_cmake_pytest</test_depend><export><build_type>ament_cmake</build_type></export></package>''')
                (pkg/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.16)
project({name})
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_pytest REQUIRED)
ament_add_pytest_test(behavior_wrapper test/test_behavior.py)
ament_package()
''')
            built = run(['colcon', 'build', '--cmake-args', '-DPython3_EXECUTABLE='+sys.executable])
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            for name, expected in [('wrapped_pass', 0), ('wrapped_skip', 2), ('wrapped_crash', 1)]:
                with self.subTest(package=name):
                    result_dir = ws/('fresh-'+name)
                    result = run(['colcon', 'test', '--packages-select', name,
                        '--return-code-on-test-failure', '--test-result-base', str(result_dir)])
                    self.assertEqual(result.returncode, 1 if name == 'wrapped_crash' else 0,
                                     result.stdout+result.stderr)
                    for selector in (None, 'behavior_wrapper', 'test_behavior'):
                        argv = [sys.executable, str(CHECK), str(result_dir), '--packages', name]
                        if selector:
                            argv += ['--require-test', name+'::'+selector]
                        checked = run(argv)
                        self.assertEqual(checked.returncode, expected, checked.stdout+checked.stderr)
            # A new CTest invocation must use its newly rewritten inner report,
            # even when the build-time result path once held a passing test.
            (ws/'src/wrapped_pass/test/test_behavior.py').write_text(
                'import pytest\n@pytest.mark.skip(reason="fixture")\ndef test_behavior():\n    assert False\n')
            fresh = ws/'second-run'
            result = run(['colcon', 'test', '--packages-select', 'wrapped_pass',
                          '--test-result-base', str(fresh)])
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            checked = run([sys.executable, str(CHECK), str(fresh), '--packages', 'wrapped_pass',
                           '--require-test', 'wrapped_pass::behavior_wrapper'])
            self.assertEqual(checked.returncode, 2, checked.stdout+checked.stderr)

if __name__ == '__main__':
    unittest.main(verbosity=2)
