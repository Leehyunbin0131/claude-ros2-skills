#!/usr/bin/env python3
"""Unit tests for the pure logic in the check_* scripts.

Runs WITHOUT ROS (rclpy is only imported inside each script's main()):
    python3 scripts/test_checks.py
"""
import math
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_imu_gravity import analyze
from check_odom_direction import yaw_from_quat, forward_displacement, verdict_for
from check_qos_compat import check_pair
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


def _qos(**over):
    base = {"reliability": "RELIABLE", "durability": "VOLATILE",
            "liveliness": "AUTOMATIC", "deadline": None, "lease": None}
    base.update(over)
    return base


def test_qos_pairs():
    # identical defaults match
    assert check_pair(_qos(), _qos()) == []
    # the classic sensor bug: BEST_EFFORT pub vs RELIABLE sub
    probs = check_pair(_qos(reliability="BEST_EFFORT"), _qos())
    assert len(probs) == 1 and "reliability" in probs[0]
    # the reverse direction is fine (RELIABLE pub, BEST_EFFORT sub)
    assert check_pair(_qos(), _qos(reliability="BEST_EFFORT")) == []
    # latched-subscriber bug: VOLATILE pub vs TRANSIENT_LOCAL sub
    probs = check_pair(_qos(), _qos(durability="TRANSIENT_LOCAL"))
    assert len(probs) == 1 and "durability" in probs[0]
    assert check_pair(_qos(durability="TRANSIENT_LOCAL"), _qos()) == []
    # liveliness: AUTOMATIC pub cannot satisfy MANUAL_BY_TOPIC sub
    assert check_pair(_qos(), _qos(liveliness="MANUAL_BY_TOPIC")) != []
    assert check_pair(_qos(liveliness="MANUAL_BY_TOPIC"), _qos()) == []
    # deadline: offered period must be <= requested; None = infinite
    assert check_pair(_qos(deadline=0.1), _qos(deadline=0.2)) == []
    assert check_pair(_qos(deadline=0.5), _qos(deadline=0.2)) != []
    assert check_pair(_qos(), _qos(deadline=0.2)) != []  # infinite offer
    assert check_pair(_qos(deadline=0.5), _qos()) == []  # sub accepts any
    # lease duration follows the same rule
    assert check_pair(_qos(lease=1.0), _qos(lease=0.5)) != []
    assert check_pair(_qos(lease=0.5), _qos(lease=1.0)) == []
    # UNKNOWN/SYSTEM_DEFAULT policies (None) are skipped, not failed
    assert check_pair(_qos(reliability=None), _qos()) == []
    # multiple simultaneous mismatches all reported
    probs = check_pair(_qos(reliability="BEST_EFFORT"),
                       _qos(durability="TRANSIENT_LOCAL", deadline=0.1))
    assert len(probs) == 3


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
