#!/usr/bin/env python3
"""Independent acceptance oracles; never imports the pack's verification scripts.

Run with Jazzy sourced and colcon/pytest available. Workspaces are rebuilt in a
new directory. Logs and results are retained in the supplied output directory.
"""
from pathlib import Path
import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from fixtures import DRIVE_GOOD, DRIVE_OLD, case_spec

MUTANTS = {
    'independent_clamp': DRIVE_OLD,
    'always_scale': '''def limit_speeds(left, right, max_speed):
    peak = max(abs(left), abs(right))
    return (left * max_speed / peak, right * max_speed / peak) if peak else (0., 0.)
''',
    'lose_signs': DRIVE_GOOD.replace('return left * scale, right * scale', 'return abs(left) * scale, abs(right) * scale'),
}


def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=3)


def command(args, cwd, log, *, timeout=120, installed=False):
    if installed:
        args = ['bash', '--noprofile', '--norc', '-c',
                'source "$1/install/setup.bash"; shift; exec "$@"', '_', str(cwd), *args]
    with log.open('w') as out:
        proc = subprocess.Popen(args, cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124
        finally:
            stop(proc)


def rebuild(source, dest):
    dest.mkdir()
    shutil.copytree(source/'src', dest/'src', symlinks=False,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    return command(['colcon', 'build', '--event-handlers', 'console_direct+'],
                   dest, dest/'build.log') == 0


def test_suite(ws):
    results = ws/'fresh-results'
    code = command(['colcon', 'test', '--python-testing', 'pytest',
                    '--return-code-on-test-failure', '--test-result-base', str(results)],
                   ws, ws/'test.log')
    cases = []
    for path in results.rglob('*.xml'):
        root = ET.parse(path).getroot()
        for case in root.iter('testcase'):
            cases.append({'name': case.get('name'),
                          'skipped': case.find('skipped') is not None,
                          'failed': case.find('failure') is not None or case.find('error') is not None})
    executed = [c for c in cases if not c['skipped'] and not (c['name'] or '').endswith('.missing_result')]
    return {'passed': code == 0 and bool(executed) and not any(c['failed'] for c in cases),
            'executed': len(executed), 'failed': sum(c['failed'] for c in cases), 'returncode': code}


def grade_tests(source, out, seed=0):
    package = case_spec(seed)['tests_package']
    ws = out/'build-candidate'
    result = {'build': rebuild(source, ws)}
    if not result['build']:
        return result
    # The API is imported from the fresh install, from outside its source tree.
    probe = '''import math
from drive_limits.limits import limit_speeds
for l,r,c in [(2.,1.,1.),(-1.,-2.,1.),(2.,-1.,1.),(0.,0.,1.),(.2,-.3,1.),(0.,4.,2.),(4.,-8.,2.),(.5,.5,.5)]:
    scale = min(1., c/max(abs(l),abs(r))) if l or r else 1.
    got = limit_speeds(l,r,c)
    assert len(got)==2 and all(math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9) for a,b in zip(got,(l*scale,r*scale))), (l,r,c,got)
print('installed behavior verified')
'''
    probe = probe.replace('from drive_limits.', f'from {package}.').replace('    scale =',
        f'    l, r, c = l * {seed+1}, r * {seed+1}, c * {seed+1}\n    scale =')
    result['installed_behavior'] = command([sys.executable, '-c', probe], ws, ws/'behavior.log', installed=True) == 0
    result['tests'] = test_suite(ws)
    if not result['installed_behavior'] or not result['tests']['passed']:
        return result
    result['test_oracles'] = {}
    # Preserve all agent tests and helper code; replace only the public function
    # with an independent implementation appended to its existing module.
    for label, implementation in {'reference': DRIVE_GOOD, **MUTANTS}.items():
        case = out/label
        staged = out/('source-'+label)
        shutil.copytree(source/'src', staged/'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        target = staged/'src'/package/package/'limits.py'
        with target.open('a') as f:
            f.write('\n'+implementation)
        built = rebuild(staged, case)
        tests = test_suite(case) if built else {'passed': False, 'executed': 0, 'failed': 0}
        if not built or tests.get('returncode') not in (0, 1):
            result.setdefault('grader_error', []).append(f'{label}: staged build/test invocation did not complete')
        # A compile failure or a runner crash does not count as rejecting a
        # mutant: an actual assertion failure must be recorded.
        result['test_oracles'][label] = built and (tests['passed'] if label == 'reference' else
            tests['executed'] > 0 and tests['failed'] > 0 and tests.get('returncode') == 1)
    return result


def launch_probe(ws, label, limit, *, argument=None, seed=0, second_namespace=False):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import Int32
    node = rclpy.create_node('acceptance_'+label)
    spec = case_spec(seed)
    namespace = spec['namespace'] + ('_other' if second_namespace else '')
    pub = node.create_publisher(LaserScan, f'/{namespace}/scan', qos_profile_sensor_data)
    seen = []
    sub = node.create_subscription(Int32, f'/{namespace}/near_count', lambda m: seen.append(m.data), qos_profile_sensor_data)
    args = ['ros2', 'launch', spec['scan_package'], 'monitor.launch.py', 'namespace:='+namespace]
    if argument is not None:
        args.append(f'limit:={argument}')
    with (ws/(label+'.log')).open('w') as log:
        proc = subprocess.Popen(['bash', '--noprofile', '--norc', '-c',
            'source "$1/install/setup.bash"; shift; exec "$@"', '_', str(ws), *args],
            cwd=ws, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        outcomes = []
        try:
            for values, low, high in [([float('nan'), float('inf'), float('-inf'), -.5, .125,
                                      .25, .375, .5, .625, .75, 1., 2., 2.5], .25, 2.),
                                     ([.25, .5, .75], .25, .5), ([], .25, 2.)]:
                msg = LaserScan()
                msg.header.frame_id = 'sim_laser'
                msg.range_min, msg.range_max, msg.ranges = low, high, values
                expected = sum(math.isfinite(x) and low <= x <= high and x <= limit for x in msg.ranges)
                seen.clear()
                deadline = time.monotonic()+12
                while time.monotonic() < deadline and proc.poll() is None:
                    msg.header.stamp = node.get_clock().now().to_msg()
                    pub.publish(msg)
                    rclpy.spin_once(node, timeout_sec=.05)
                    if len(seen) >= 4 and seen[-4:] == [expected]*4:
                        break
                    time.sleep(.025)
                endpoints = [*node.get_subscriptions_info_by_topic(f'/{namespace}/scan'),
                             *node.get_publishers_info_by_topic(f'/{namespace}/near_count')]
                namespaced = len(endpoints) >= 2 and all(e.node_namespace == '/'+namespace for e in endpoints)
                outcomes.append({'expected': expected, 'observed': seen[-8:], 'nodes_namespaced': namespaced,
                                 'passed': len(seen) >= 4 and seen[-4:] == [expected]*4 and namespaced})
                if not outcomes[-1]['passed']:
                    break
        finally:
            stop(proc)
            node.destroy_subscription(sub)
            node.destroy_publisher(pub)
            node.destroy_node()
    return outcomes


def grade_scan(source, out, seed=0):
    import rclpy
    import yaml
    ws = out/'build-candidate'
    result = {'build': rebuild(source, ws)}
    if not result['build']:
        return result
    result['tests'] = test_suite(ws)
    spec = case_spec(seed)
    package = spec['scan_package']
    config = ws/'install'/package/'share'/package/'config/monitor.yaml'
    result['yaml_installed'] = config.is_file()
    if not config.is_file():
        return result
    original = yaml.safe_load(config.read_text())
    # The task specifies the parameter and file path; retain whatever node-key
    # structure the agent selected and mutate only this parameter.
    def replace_limit(obj):
        found = 0
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'ros__parameters' and isinstance(value, dict) and 'limit' in value:
                    value['limit'] = spec['mutated_limit']
                    found += 1
                else:
                    found += replace_limit(value)
        return found
    rclpy.init()
    try:
        result['default'] = launch_probe(ws, 'default', spec['default_limit'], seed=seed)
        if not all(case['passed'] for case in result['default']):
            return result
        result['yaml_parameter_present'] = replace_limit(original) > 0
        config.write_text(yaml.safe_dump(original))
        result['yaml_effective'] = launch_probe(ws, 'yaml', spec['mutated_limit'], seed=seed)
        result['argument_override'] = launch_probe(ws, 'override', spec['argument_limit'], argument=spec['argument_limit'], seed=seed, second_namespace=True)
    finally:
        rclpy.try_shutdown()
    return result


def passed(task, result):
    if result.get('grader_error'):
        return False
    if not result.get('build'):
        return False
    if not result.get('tests', {}).get('passed'):
        return False
    if task == 'tests':
        return result.get('installed_behavior', False) and len(result.get('test_oracles', {})) == 4 and all(result['test_oracles'].values())
    return (result.get('yaml_installed', False) and result.get('yaml_parameter_present', False) and
            all(len(result.get(k, [])) == 3 and all(p['passed'] for p in result[k])
                for k in ('default', 'yaml_effective', 'argument_override')))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('task', choices=('scan', 'tests'))
    ap.add_argument('workspace', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = (grade_scan if args.task == 'scan' else grade_tests)(args.workspace.resolve(), args.output.resolve(), args.seed)
    result['accepted'] = passed(args.task, result)
    result['gradable'] = not bool(result.get('grader_error'))
    (args.output/'verdict.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 2 if not result['gradable'] else 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
