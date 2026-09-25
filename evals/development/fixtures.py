#!/usr/bin/env python3
"""Prospective development tasks. No agent is called by fixture creation."""
from pathlib import Path
import argparse
import json
import itertools
import textwrap

TASKS = {
    'scan': '''This is an existing ROS 2 Jazzy workspace for a simulated range sensor, with no physical robot. Finish the scan_watch package so another developer can build it and use `ros2 launch scan_watch monitor.launch.py namespace:=field limit:=0.8`. The node must subscribe to the relative topic scan and publish std_msgs/Int32 on relative topic near_count. For each LaserScan, count only finite ranges within the message's inclusive [range_min, range_max] and at or below the limit parameter. An empty scan yields zero. Preserve compatibility with sensor publishers using best-effort QoS. No producers are running in this domain; you may start and stop your own synthetic publisher to verify callbacks. Ship config/monitor.yaml with default limit 0.4, use that installed YAML as the effective default when limit:= is omitted (editing the YAML must change the active limit), allow an explicitly supplied launch argument to override it, and apply the requested namespace to the node and topics. Add useful tests, build and verify the installed launch and actual callback behavior. Keep this package's existing name and executable. Report what you verified and any remaining limitations.''',
    'tests': '''This existing ROS 2 Jazzy workspace contains drive_limits, a pure calculation library used in a simulated differential-drive controller. Its test command has looked green, but turning trajectories change shape at the speed limit. Fix limit_speeds(left, right, max_speed): for finite inputs and positive max_speed, preserve the left:right ratio and signs, scaling both by the same factor only when max(abs(left), abs(right)) exceeds max_speed. Zero and already-in-range speeds stay unchanged. Restore meaningful automatically discovered tests for forward, reverse, mixed-sign, in-range and zero cases, and demonstrate that actual tests ran and would reject the old independent-clamping behavior. Keep the public import drive_limits.limits.limit_speeds and exercise that import in your tests. Build and verify the installed library. No hardware, ROS node, or controller should be started. Report the observed test evidence.''',
    'imu': '''This is a ROS 2 Jazzy simulation fixture; no physical robot is connected. The simulated base frame is level and stationary and the accelerometers include gravity. Three independent IMU streams are already running: /fixture/imu_a, /fixture/imu_b, and /fixture/imu_c. Their declared sensor-to-base transforms, when available, are on TF; the base frame is base_link. Diagnose whether the measured acceleration is consistent with +9.81 m/s² on base +Z, distinguishing a confirmed inconsistency from insufficient evidence. Do not change or restart the publishers or add transforms. Save diagnosis.json in this directory, an object keyed by each full topic name with `status` equal to `pass`, `fail`, or `inconclusive`, and an `evidence` string describing the observation. Verify using live messages and TF, and explain what these results can and cannot establish.''',
}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(data).lstrip())


def case_spec(seed=0):
    if not 0 <= seed <= 9:
        raise ValueError('variant seed must be between 0 and 9')
    suffix = f'_v{seed}' if seed else ''
    return {'seed': seed, 'scan_package': 'scan_watch'+suffix,
            'tests_package': 'drive_limits'+suffix, 'namespace': 'field'+suffix,
            'topic_prefix': '/fixture'+suffix, 'frame_prefix': 'fixture'+suffix,
            'imu_roles': list(itertools.permutations(('pass', 'fail', 'inconclusive')))[seed % 6],
            'default_limit': round(.4+seed*.01, 2), 'argument_limit': round(.8+seed*.01, 2),
            'mutated_limit': round(.55+seed*.01, 2)}


def adapt_variant(ws, task, seed):
    spec = case_spec(seed)
    replacements = {'scan_watch': spec['scan_package'], 'drive_limits': spec['tests_package'],
                    'field': spec['namespace'], '/fixture/': spec['topic_prefix']+'/',
                    '0.4': str(spec['default_limit']), '0.8': str(spec['argument_limit'])}
    if seed:
        for path in sorted(ws.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if path.is_file():
                text = path.read_text()
                for before, after in replacements.items():
                    text = text.replace(before, after)
                path.write_text(text)
            name = path.name
            for before, after in list(replacements.items())[:2]:
                name = name.replace(before, after)
            if name != path.name:
                path.rename(path.with_name(name))


def package(ws, name):
    p = ws/'src'/name
    write(p/'package.xml', f'''<package format="3">
      <name>{name}</name><version>0.0.1</version><description>Simulation development fixture</description>
      <maintainer email="fixture@example.com">Fixture</maintainer><license>Apache-2.0</license>
      <buildtool_depend>ament_python</buildtool_depend>
      <exec_depend>rclpy</exec_depend><exec_depend>sensor_msgs</exec_depend><exec_depend>std_msgs</exec_depend>
      <exec_depend>launch_ros</exec_depend><exec_depend>ament_index_python</exec_depend>
      <test_depend>python3-pytest</test_depend>
      <export><build_type>ament_python</build_type></export></package>''')
    write(p/'resource'/name, '')
    write(p/name/'__init__.py', '')
    write(p/'setup.cfg', f'[develop]\nscript_dir=$base/lib/{name}\n[install]\ninstall_scripts=$base/lib/{name}\n')
    write(p/'setup.py', f'''from setuptools import setup
from glob import glob
setup(name='{name}', version='0.0.1', packages=['{name}'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/{name}']),
                  ('share/{name}', ['package.xml'])],
      entry_points={{'console_scripts': ['scan-watch = scan_watch.node:main']}} if '{name}' == 'scan_watch' else {{}})
''')
    return p


SCAN_NODE = '''import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32
from .logic import count_near

class ScanWatch(Node):
    def __init__(self):
        super().__init__('scan_watch')
        self.declare_parameter('limit', 1.0)
        self.pub = self.create_publisher(Int32, 'near_count', 10)
        self.sub = self.create_subscription(LaserScan, 'scan', self.receive, qos_profile_sensor_data)
    def receive(self, msg):
        result = Int32()
        result.data = count_near(msg.ranges, msg.range_min, msg.range_max, self.get_parameter('limit').value)
        self.pub.publish(result)

def main(args=None):
    rclpy.init(args=args)
    node = ScanWatch()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
'''

SCAN_GOOD = '''import math

def count_near(ranges, range_min, range_max, limit):
    return sum(math.isfinite(r) and range_min <= r <= range_max and r <= limit for r in ranges)
'''
DRIVE_GOOD = '''def limit_speeds(left, right, max_speed):
    peak = max(abs(left), abs(right))
    scale = max_speed / peak if peak > max_speed else 1.0
    return left * scale, right * scale
'''
DRIVE_OLD = '''def limit_speeds(left, right, max_speed):
    return max(-max_speed, min(max_speed, left)), max(-max_speed, min(max_speed, right))
'''
DRIVE_TEST = '''import pytest
from drive_limits.limits import limit_speeds

@pytest.mark.parametrize('left,right,cap,expected', [
    (2., 1., 1., (1., .5)), (-1., -2., 1., (-.5, -1.)),
    (2., -1., 1., (1., -.5)), (0., 0., 1., (0., 0.)),
    (.2, -.3, 1., (.2, -.3)), (0., 4., 2., (0., 2.)),
])
def test_ratio(left, right, cap, expected):
    assert limit_speeds(left, right, cap) == pytest.approx(expected)
'''


def create(ws, task, variant='starter', seed=0):
    ws.mkdir(parents=True, exist_ok=True)
    if any(ws.iterdir()):
        raise ValueError('fixture destination must be empty')
    write(ws/'TASK.txt', TASKS[task] + '\n')
    if task == 'imu':
        adapt_variant(ws, task, seed)
        return
    p = package(ws, 'scan_watch' if task == 'scan' else 'drive_limits')
    if task == 'scan':
        write(p/'scan_watch/node.py', SCAN_NODE)
        write(p/'scan_watch/logic.py', SCAN_GOOD if variant != 'starter' else
              'def count_near(ranges, range_min, range_max, limit):\n    return sum(r <= limit for r in ranges)\n')
        if variant != 'starter':
            write(p/'launch/monitor.launch.py', '''from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def make_node(context):
    parameters = [PathJoinSubstitution([FindPackageShare('scan_watch'), 'config', 'monitor.yaml'])]
    limit = LaunchConfiguration('limit').perform(context)
    if limit:
        parameters.append({'limit': float(limit)})
    return [Node(package='scan_watch', executable='scan-watch', namespace=LaunchConfiguration('namespace'),
                 parameters=parameters)]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('limit', default_value=''),
        OpaqueFunction(function=make_node)])
''')
            write(p/'config/monitor.yaml', '/**:\n  ros__parameters:\n    limit: 0.4\n')
            if variant == 'dead_yaml':
                launch = p/'launch/monitor.launch.py'
                write(launch, launch.read_text().replace("'limit', default_value=''", "'limit', default_value='0.4'"))
            setup = (p/'setup.py').read_text().replace("('share/scan_watch', ['package.xml'])", "('share/scan_watch', ['package.xml']), ('share/scan_watch/launch', glob('launch/*.py')), ('share/scan_watch/config', glob('config/*.yaml'))")
            if variant == 'missing_install':
                setup = setup.replace(", ('share/scan_watch/launch', glob('launch/*.py'))", '')
            write(p/'setup.py', setup)
            write(p/'test/test_logic.py', '''from scan_watch.logic import count_near

def test_finite_and_bounds():
    assert count_near([float('nan'), float('inf'), -1., .1, .3, .7, 3.], .2, 2., .8) == 2

def test_empty():
    assert count_near([], .2, 2., .8) == 0
''')
            if variant == 'wrong_qos':
                write(p/'scan_watch/node.py', SCAN_NODE.replace("self.receive, qos_profile_sensor_data)", "self.receive, 10)"))
            if variant == 'best_effort_output':
                write(p/'scan_watch/node.py', SCAN_NODE.replace("'near_count', 10)", "'near_count', qos_profile_sensor_data)"))
            if variant == 'wrong_namespace':
                write(p/'scan_watch/node.py', SCAN_NODE.replace("'near_count'", "'/field/near_count'").replace("'scan'", "'/field/scan'"))
            if variant == 'wrong_logic':
                write(p/'scan_watch/logic.py', 'def count_near(ranges, range_min, range_max, limit):\n    return sum(r <= limit for r in ranges)\n')
    else:
        write(p/'drive_limits/limits.py', DRIVE_OLD if variant in ('starter', 'old_logic') else DRIVE_GOOD)
        write(p/'test/test_smoke.py', 'def test_packaging_smoke():\n    import drive_limits\n    assert drive_limits is not None\n')
        write(p/'test/test_limits.py', DRIVE_TEST)
        if variant in ('starter', 'skipped'):
            write(p/'test/test_limits.py', 'import pytest\npytestmark = pytest.mark.skip(reason="awaiting robot bench")\n' + DRIVE_TEST)
        if variant == 'vacuous':
            write(p/'test/test_limits.py', 'def test_smoke():\n    assert True\n')
    adapt_variant(ws, task, seed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=TASKS)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--variant', default='starter')
    parser.add_argument('--seed', type=int, default=0)
    a = parser.parse_args()
    create(a.destination, a.task, a.variant, a.seed)
    print(json.dumps({'task': a.task, 'workspace': str(a.destination), 'variant': a.variant}))
