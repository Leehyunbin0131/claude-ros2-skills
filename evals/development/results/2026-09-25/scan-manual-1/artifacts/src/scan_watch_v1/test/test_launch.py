"""Run the installed monitor.launch.py and exercise the launched node over ROS topics.

Requires the package to be installed and sourced (as under `colcon test`).
"""
import os
import signal
import subprocess
import sys
import time
import uuid

import pytest
import yaml
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError

sys.path.insert(0, os.path.dirname(__file__))
from probe import Probe, exchange, make_scan, new_executor  # noqa: E402

# limit 0.41 -> 2, 0.6 -> 3, 0.81 -> 4
RANGES = [0.3, 0.41, 0.6, 0.81, 0.9]

try:
    SHARE = get_package_share_directory('scan_watch_v1')
except PackageNotFoundError:
    SHARE = None
pytestmark = pytest.mark.skipif(SHARE is None, reason='scan_watch_v1 is not installed')


def _launch(*args):
    return subprocess.Popen(
        ['ros2', 'launch', 'scan_watch_v1', 'monitor.launch.py', *args],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)


def _stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    return proc.stdout.read()


def _wait_for_node(executor, probe, ns, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if ('scan_watch_v1', f'/{ns}') in probe.get_node_names_and_namespaces():
            return
        executor.spin_once(timeout_sec=0.1)
    raise TimeoutError(f'/{ns}/scan_watch_v1 not discovered')


def _run(ros_context, extra_args):
    ns = 'test_launch_' + uuid.uuid4().hex[:8]
    proc = _launch(f'namespace:={ns}', *extra_args)
    probe = Probe(ns, ros_context)
    ex = new_executor(ros_context, probe)
    try:
        _wait_for_node(ex, probe, ns)
        count = exchange(ex, probe, make_scan(RANGES))
    finally:
        ex.shutdown()
        probe.destroy_node()
        output = _stop(proc)
        print(output)
    # Ctrl-C must stop the node cleanly, not with a traceback.
    assert proc.returncode == 0, output
    assert 'process has died' not in output and 'Traceback' not in output, output
    return count


def test_installed_yaml_default_limit():
    with open(os.path.join(SHARE, 'config', 'monitor.yaml')) as f:
        params = yaml.safe_load(f)
    assert params['/**']['ros__parameters']['limit'] == 0.41


def test_launch_uses_yaml_when_limit_omitted(ros_context):
    assert _run(ros_context, []) == 2


def test_launch_limit_argument_overrides_yaml(ros_context):
    assert _run(ros_context, ['limit:=0.81']) == 4


def test_launch_integer_limit_argument(ros_context):
    assert _run(ros_context, ['limit:=1']) == 5


def test_launch_follows_edited_yaml(ros_context, tmp_path):
    edited = tmp_path / 'monitor.yaml'
    edited.write_text('/**:\n  ros__parameters:\n    limit: 0.6\n')
    assert _run(ros_context, [f'params_file:={edited}']) == 3
    # An explicit limit still wins over the edited file.
    assert _run(ros_context, [f'params_file:={edited}', 'limit:=0.81']) == 4
