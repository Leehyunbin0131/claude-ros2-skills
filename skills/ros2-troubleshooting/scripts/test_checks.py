#!/usr/bin/env python3
"""Unit tests for the pure logic in the check_* scripts.

Runs WITHOUT ROS (rclpy is only imported inside each script's main()):
    python3 skills/ros2-troubleshooting/scripts/test_checks.py
"""
import math
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_imu_gravity import analyze, rotate_acceleration
from check_odom_direction import yaw_from_quat, forward_displacement, verdict_for
from check_qos_compat import compatibility_verdict, combined_verdict
from _check_common import exit_code
from check_tf_tree import quat_to_rpy, describe_mount

G = 9.81


def q_from_yaw(yaw):
    return (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))


def test_imu():
    # correct mounting: gravity on +Z
    assert analyze([(0.0, 0.1, 9.8)] * 10)[0] == "PASS"
    # upside-down: -Z
    assert analyze([(0.0, 0.0, -9.8)] * 10)[0] == "FAIL"
    # rotated 90 deg: gravity on X
    assert analyze([(9.8, 0.0, 0.1)] * 10)[0] == "FAIL"
    # robot moving / bad scale: wrong magnitude
    assert analyze([(0.0, 0.0, 5.0)] * 10)[0] == "FAIL"
    # tilted mount: split axes
    assert analyze([(5.0, 5.0, 5.66)] * 10)[0] == "FAIL"
    # no data
    assert analyze([])[0] == "INCONCLUSIVE"
    # noisy but centered on +Z: averaging works
    noisy = [(0.05, -0.05, 9.75), (-0.05, 0.05, 9.85)] * 10
    assert analyze(noisy)[0] == "PASS"


def test_yaw_from_quat():
    for yaw in (0.0, 0.5, math.pi / 2, -math.pi / 2, 3.0, -3.0):
        x, y, z, w = q_from_yaw(yaw)
        assert abs(yaw_from_quat(x, y, z, w) - yaw) < 1e-9, yaw


def test_imu_transform():
    # A correctly declared upside-down IMU is healthy in the robot base frame.
    corrected = rotate_acceleration((0.0, 0.0, -G), (1.0, 0.0, 0.0, 0.0))
    assert analyze([corrected])[0] == 'PASS'
    s = math.sqrt(0.5)
    corrected = rotate_acceleration((-G, 0.0, 0.0), (0.0, s, 0.0, s))
    assert analyze([corrected])[0] == 'PASS'
    assert analyze([(0.0, 0.0, -G)])[0] == 'FAIL'


def test_forward_displacement():
    # heading +x, moved +1 in x -> forward
    assert abs(forward_displacement((0, 0, 0.0), (1.0, 0.0, 0.0)) - 1.0) < 1e-9
    # heading +x, moved -1 in x -> backward
    assert abs(forward_displacement((0, 0, 0.0), (-1.0, 0.0, 0.0)) + 1.0) < 1e-9
    # heading +y (yaw 90 deg), moved +1 in y -> forward
    assert abs(forward_displacement((0, 0, math.pi / 2), (0.0, 1.0, 0.0)) - 1.0) < 1e-9
    # heading -x (yaw 180), moved +1 in x -> backward
    assert abs(forward_displacement((0, 0, math.pi), (1.0, 0.0, 0.0)) + 1.0) < 1e-9
    # start away from origin
    assert abs(forward_displacement((5, 5, 0.0), (6.0, 5.0, 0.0)) - 1.0) < 1e-9


def test_verdict():
    assert verdict_for(0.9, 1.0)[0] == "PASS"
    assert verdict_for(-0.9, 1.0)[0] == "FAIL"
    assert verdict_for(0.05, 1.0)[0] == "INCONCLUSIVE"
    assert verdict_for(-0.05, 1.0)[0] == "INCONCLUSIVE"


def test_quat_to_rpy():
    # identity
    r, p, y = quat_to_rpy(0, 0, 0, 1)
    assert max(abs(r), abs(p), abs(y)) < 1e-9
    # pure yaw 90 deg
    x, yy, z, w = q_from_yaw(math.pi / 2)
    r, p, y = quat_to_rpy(x, yy, z, w)
    assert abs(r) < 1e-9 and abs(p) < 1e-9 and abs(y - math.pi / 2) < 1e-9
    # roll 180 deg (upside-down sensor): q = (1, 0, 0, 0)
    r, p, y = quat_to_rpy(1, 0, 0, 0)
    assert abs(abs(r) - math.pi) < 1e-9
    # pitch 90 deg (gimbal edge): q = (0, sin(45), 0, cos(45)) — must not crash
    s45 = math.sin(math.pi / 4)
    r, p, y = quat_to_rpy(0, s45, 0, s45)
    assert abs(p - math.pi / 2) < 1e-6


def test_qos_verdicts():
    assert compatibility_verdict('OK') == 'PASS'
    assert compatibility_verdict('ERROR') == 'FAIL'
    assert compatibility_verdict('WARNING') == 'INCONCLUSIVE'
    assert compatibility_verdict('UNKNOWN') == 'INCONCLUSIVE'
    assert combined_verdict([]) == 'INCONCLUSIVE'
    assert combined_verdict(['PASS', 'PASS']) == 'PASS'
    assert combined_verdict(['PASS', 'INCONCLUSIVE']) == 'INCONCLUSIVE'
    assert combined_verdict(['INCONCLUSIVE', 'FAIL', 'PASS']) == 'FAIL'


def test_invalid_measurements():
    for value in (float('nan'), float('inf'), -float('inf')):
        for axis in range(3):
            sample = [0.0, 0.0, G]
            sample[axis] = value
            assert analyze([tuple(sample)])[0] == 'INCONCLUSIVE'
        assert verdict_for(value, 1.0)[0] == 'INCONCLUSIVE'
    for q in [(0, 0, 0, 0), (0, 0, 0, 2), (0, float('nan'), 0, 1)]:
        for convert in (yaw_from_quat, quat_to_rpy):
            try:
                convert(*q)
            except ValueError:
                pass
            else:
                raise AssertionError(f'{convert.__name__} accepted invalid {q}')


def test_exit_codes():
    for verdict, expected in [('PASS', 0), ('FAIL', 1), ('INCONCLUSIVE', 2)]:
        assert exit_code(verdict) == expected
    assert exit_code(verdict_for(0.0, 1.0)[0]) == 2
    assert exit_code(analyze([(0.0, float('nan'), G)])[0]) == 2


def test_cli_arguments():
    import subprocess
    base = pathlib.Path(__file__).resolve().parent
    for script, arguments in [
        ('check_imu_gravity.py', ['--samples', '0']),
        ('check_imu_gravity.py', ['--timeout', 'nan']),
        ('check_imu_gravity.py', ['--tol-mag', 'inf']),
        ('check_odom_direction.py', ['--dist', '-1']),
        ('check_odom_direction.py', ['--wait-secs', '-1']),
        ('check_odom_direction.py', ['--timeout', 'inf']),
        ('check_qos_compat.py', ['--topic', '/test', '--wait', 'nan']),
        ('check_tf_tree.py', ['--timeout', '-1']),
    ]:
        result = subprocess.run([sys.executable, str(base / script), *arguments],
                                text=True, capture_output=True, timeout=5)
        assert result.returncode == 2, (script, arguments, result)
        assert 'error: argument' in result.stderr, result.stderr
        assert 'Traceback' not in result.stderr, result.stderr


def test_describe_mount():
    assert any("UPSIDE-DOWN" in w for w in describe_mount(180.0, 0.0, 0.0))
    assert any("BACKWARD" in w for w in describe_mount(0.0, 0.0, 179.0))
    assert any("BACKWARD" in w for w in describe_mount(0.0, 0.0, -180.0))
    assert describe_mount(0.0, 0.0, 0.0) == []
    assert describe_mount(2.0, -3.0, 90.0) == []  # 90 deg yaw is a legit side mount


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} test groups passed.")
