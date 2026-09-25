from array import array
import math

import pytest

from scan_watch.logic import count_near

INF = math.inf
NAN = math.nan


def f32(values):
    """Ranges as they arrive in a LaserScan message (float32 array)."""
    return array('f', values)


def test_empty_scan_is_zero():
    assert count_near([], 0.1, 10.0, 1.0) == 0
    assert count_near(f32([]), 0.1, 10.0, 1.0) == 0


def test_non_finite_ranges_are_ignored():
    assert count_near([INF, -INF, NAN], 0.0, INF, INF) == 0


def test_bounds_are_inclusive():
    assert count_near([0.1, 2.0], 0.1, 2.0, 5.0) == 2


def test_ranges_outside_message_bounds_are_ignored():
    assert count_near([0.05, 2.5, -1.0], 0.1, 2.0, 5.0) == 0


def test_limit_is_inclusive():
    assert count_near([0.3, 0.4, 0.5], 0.0, 10.0, 0.4) == 2


def test_limit_equal_to_float32_range_counts():
    # float32(0.4) > float64(0.4); a reading of exactly 0.4 is still "at" the limit.
    assert count_near(f32([0.4, 0.8]), 0.0, 10.0, 0.4) == 1
    assert count_near(f32([0.4, 0.8]), 0.0, 10.0, 0.8) == 2


def test_limit_below_range_min_counts_nothing():
    assert count_near([0.1, 0.2], 0.5, 10.0, 0.3) == 0


@pytest.mark.parametrize('limit, expected', [(0.4, 3), (0.8, 5), (1e300, 7), (-1.0, 0)])
def test_mixed_scan(limit, expected):
    ranges = f32([0.05, 0.1, 0.3, 0.4, 0.5, 0.8, 1.0, 2.0, 2.5, INF, NAN, -INF])
    assert count_near(ranges, 0.1, 2.0, limit) == expected
