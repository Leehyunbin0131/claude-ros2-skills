"""Run the installed monitor.launch.py through `ros2 launch` and exercise the callback."""
import os
import signal
import subprocess

import pytest
import yaml
from ament_index_python.packages import get_package_share_directory

from conftest import Probe, make_scan, unique_namespace

SHARE = get_package_share_directory('scan_watch_v2')
INSTALLED_YAML = os.path.join(SHARE, 'config', 'monitor.yaml')


@pytest.fixture
def launch():
    procs = []

    def start(*args):
        proc = subprocess.Popen(
            ['ros2', 'launch', 'scan_watch_v2', 'monitor.launch.py', *args],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True)
        procs.append(proc)
        return proc

    yield start
    for proc in procs:
        # Only signal the process group this fixture created.
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        if not proc.stdout.closed:
            print(proc.stdout.read())


def test_installed_yaml_default_is_042():
    with open(INSTALLED_YAML) as f:
        data = yaml.safe_load(f)
    assert data['/**']['ros__parameters']['limit'] == 0.42


def test_launch_uses_installed_yaml_when_limit_omitted(ros, launch):
    ns = unique_namespace()
    launch(f'namespace:={ns.lstrip("/")}')
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 2
    # Node-name discovery can lag behind endpoint discovery.
    assert probe.spin_until(
        lambda: ('scan_watch_v2', ns) in ros[0].get_node_names_and_namespaces(), 10.0)


def test_launch_limit_argument_overrides_yaml(ros, launch):
    ns = unique_namespace()
    launch(f'namespace:={ns.lstrip("/")}', 'limit:=0.82')
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 5
    assert probe.exchange(make_scan([])) == 0


def test_launch_reads_limit_from_params_file(ros, launch, tmp_path):
    # Same mechanism as the default installed YAML, with a value unlike the node default.
    params = tmp_path / 'monitor.yaml'
    params.write_text('/**:\n  ros__parameters:\n    limit: 0.6\n')
    ns = unique_namespace()
    launch(f'namespace:={ns.lstrip("/")}', f'params_file:={params}')
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 3


def test_launch_sigint_shuts_node_down_cleanly(ros, launch):
    ns = unique_namespace()
    proc = launch(f'namespace:={ns.lstrip("/")}')
    probe = Probe(ros[0], ros[1], ns)
    assert probe.exchange(make_scan()) == 2
    os.killpg(proc.pid, signal.SIGINT)
    out, _ = proc.communicate(timeout=15)
    assert 'Traceback' not in out, out
    assert 'process has finished cleanly' in out, out


def test_launch_rejects_non_numeric_limit(launch):
    proc = launch('limit:=far')
    out, _ = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert "limit:='far' is not a finite number" in out, out
