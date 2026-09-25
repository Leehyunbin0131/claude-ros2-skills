import importlib.util
import os

import pytest
import yaml

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(PKG_DIR, 'config', 'monitor.yaml')


def _load_launch_module():
    path = os.path.join(PKG_DIR, 'launch', 'monitor.launch.py')
    spec = importlib.util.spec_from_file_location('monitor_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_yaml_default_limit_applies_to_any_namespace():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    assert data == {'/**': {'ros__parameters': {'limit': 0.4}}}


def test_omitted_limit_uses_only_yaml():
    build = _load_launch_module().build_parameters
    assert build('/p/monitor.yaml', '') == ['/p/monitor.yaml']


def test_explicit_limit_overrides_yaml():
    build = _load_launch_module().build_parameters
    # Later entries win in launch_ros, so the override must come last.
    assert build('/p/monitor.yaml', '0.8') == ['/p/monitor.yaml', {'limit': 0.8}]
    assert build('/p/monitor.yaml', '1') == ['/p/monitor.yaml', {'limit': 1.0}]


@pytest.mark.parametrize('bad', ['abc', 'nan'])
def test_invalid_limit_rejected(bad):
    build = _load_launch_module().build_parameters
    with pytest.raises(ValueError):
        build('/p/monitor.yaml', bad)
