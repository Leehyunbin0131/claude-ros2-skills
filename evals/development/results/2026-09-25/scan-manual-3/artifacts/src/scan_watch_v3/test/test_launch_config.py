import importlib.util
import os

import pytest
import yaml

PKG = os.path.join(os.path.dirname(__file__), '..')


def load_launch_module():
    path = os.path.join(PKG, 'launch', 'monitor.launch.py')
    spec = importlib.util.spec_from_file_location('monitor_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shipped_default_limit():
    with open(os.path.join(PKG, 'config', 'monitor.yaml')) as f:
        data = yaml.safe_load(f)
    assert data == {'/**/scan_watch_v3': {'ros__parameters': {'limit': 0.43}}}


def test_omitted_limit_uses_only_yaml():
    launch = load_launch_module()
    assert launch.monitor_parameters('/p/monitor.yaml', '') == ['/p/monitor.yaml']


def test_explicit_limit_overrides_yaml():
    launch = load_launch_module()
    assert launch.monitor_parameters('/p/monitor.yaml', '0.83') == [
        '/p/monitor.yaml', {'limit': 0.83}]
    assert launch.monitor_parameters('/p/monitor.yaml', '1') == [
        '/p/monitor.yaml', {'limit': 1.0}]


def test_invalid_limit_fails_clearly():
    launch = load_launch_module()
    with pytest.raises(RuntimeError, match='not a number'):
        launch.monitor_parameters('/p/monitor.yaml', 'near')


def test_launch_arguments_declared():
    launch = load_launch_module()
    names = [a.name for a in launch.generate_launch_description().get_launch_arguments()]
    assert names == ['namespace', 'limit']
