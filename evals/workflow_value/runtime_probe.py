#!/usr/bin/env python3
"""Independent interface and runtime observation of a freshly built workspace.

Run only inside a shell that sourced /opt/ros/jazzy and the grader's fresh
``install/setup.bash``. Starts both documented ``monitor`` executables in their
own process groups, drives the documented input topic from an independent
publisher, and stops only the processes it started. Prints one JSON object.
"""
from pathlib import Path
import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import spec  # noqa: E402


def interface(s):
    try:
        module = __import__(f"{s['interface_package']}.msg", fromlist=[s['msg']])
        fields = dict(getattr(module, s['msg']).get_fields_and_field_types())
    except Exception as error:  # noqa: BLE001 - report any import failure as evidence
        return {'importable': False, 'error': f'{type(error).__name__}: {error}'}
    return {'importable': True, 'fields': fields,
            'new_field': fields.get(s['new_field']) == 'double',
            'valid_field': fields.get('valid') == 'boolean',
            'old_field_absent': s['old_field'] not in fields}


def start(package, logdir):
    log = open(Path(logdir) / f'{package}.log', 'w')
    proc = subprocess.Popen(['ros2', 'run', package, 'monitor'], stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    return proc, log


def stop(proc):
    if proc.poll() is None:
        for sig, wait in ((signal.SIGINT, 5), (signal.SIGTERM, 3), (signal.SIGKILL, 3)):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.wait(timeout=wait)
                break
            except subprocess.TimeoutExpired:
                continue
    try:  # the group may outlive its leader
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return proc.returncode


def matches(value, expected):
    if math.isnan(expected):
        return math.isnan(value)
    return math.isfinite(value) and abs(value - expected) <= 1e-9 * max(1.0, abs(expected))


def runtime(s, logdir, discovery=20.0, per_case=10.0):
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from std_msgs.msg import Float64
    module = __import__(f"{s['interface_package']}.msg", fromlist=[s['msg']])
    message_type = getattr(module, s['msg'])
    procs = {}
    result = {'cases': [], 'discovered': False}
    node = None
    try:
        for name in ('py', 'cpp'):
            procs[name] = start(s[f'{name}_package'], logdir)
        rclpy.init()
        node = rclpy.create_node('workflow_value_probe')
        publisher = node.create_publisher(message_type, s['input_topic'], QoSProfile(
            depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE))
        # Best effort accepts reliable or best-effort output publishers.
        output_qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT,
                                durability=DurabilityPolicy.VOLATILE)
        seen = {'py': [], 'cpp': []}
        subscriptions = [node.create_subscription(
            Float64, s[f'{name}_topic'], lambda m, n=name: seen[n].append(m.data), output_qos)
            for name in ('py', 'cpp')]
        ready = False
        deadline = time.monotonic() + discovery
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            ready = (publisher.get_subscription_count() >= 2 and
                     all(node.count_publishers(s[f'{n}_topic']) >= 1 for n in ('py', 'cpp')))
            if ready or any(p.poll() is not None for p, _ in procs.values()):
                break
        result['discovered'] = ready
        result['exited_early'] = {n: p.poll() for n, (p, _) in procs.items()}
        if ready:
            cases = [(v, True, v) for v in s['runtime_valid']]
            cases.append((s['runtime_invalid'], False, math.nan))
            for value, valid, expected in cases:
                for values in seen.values():
                    values.clear()
                message = message_type()
                setattr(message, s['new_field'], float(value))
                message.valid = valid
                ok = {}
                end = time.monotonic() + per_case
                while time.monotonic() < end:
                    publisher.publish(message)
                    stop_at = time.monotonic() + 0.1
                    while time.monotonic() < stop_at:
                        rclpy.spin_once(node, timeout_sec=0.02)
                    ok = {n: len(v) >= 3 and all(matches(x, expected) for x in v[-3:])
                          for n, v in seen.items()}
                    if all(ok.values()):
                        break
                result['cases'].append({
                    'value': value, 'valid': valid, 'expected': 'nan' if math.isnan(expected) else expected,
                    'observed': {n: [repr(x) for x in v[-5:]] for n, v in seen.items()},
                    'passed': ok})
        for subscription in subscriptions:
            node.destroy_subscription(subscription)
        node.destroy_publisher(publisher)
    except Exception as error:  # noqa: BLE001 - reported as evidence, children still stopped
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
        result['exit_codes'] = {}
        for name, (proc, log) in procs.items():
            result['exit_codes'][name] = stop(proc)
            log.close()
    result['passed'] = {n: bool(result['cases']) and all(c['passed'].get(n) for c in result['cases'])
                        for n in ('py', 'cpp')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--logdir', type=Path, required=True)
    args = parser.parse_args()
    s = spec(args.seed)
    report = {'interface': interface(s)}
    iface = report['interface']
    if iface.get('importable') and iface['new_field'] and iface['valid_field']:
        report['runtime'] = runtime(s, args.logdir)
    else:
        report['runtime'] = {'skipped': 'interface lacks the requested fields',
                             'passed': {'py': False, 'cpp': False}}
    print(json.dumps(report))


if __name__ == '__main__':
    main()
