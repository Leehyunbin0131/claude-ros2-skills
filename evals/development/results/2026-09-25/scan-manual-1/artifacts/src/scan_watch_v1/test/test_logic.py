import array
import math

import pytest

from scan_watch_v1.logic import count_near

INF = math.inf
NAN = math.nan


def test_empty_scan_is_zero():
    assert count_near([], 0.1, 10.0, 0.41) == 0


def test_counts_at_or_below_limit():
    assert count_near([0.2, 0.41, 0.42, 1.0], 0.1, 10.0, 0.41) == 2


@pytest.mark.parametrize('value', [INF, -INF, NAN])
def test_non_finite_ignored_even_with_infinite_limit(value):
    assert count_near([value, 0.3], 0.0, INF, INF) == 1


def test_bounds_are_inclusive():
    assert count_near([0.1, 0.5], 0.1, 0.5, 1.0) == 2


def test_outside_range_min_max_ignored():
    # Below range_min (e.g. 0.0 "no return") and above range_max are discarded.
    assert count_near([0.0, 0.05, 0.2, 6.0], 0.1, 5.0, 10.0) == 1


def test_negative_values_ignored():
    assert count_near([-0.2, 0.2], 0.1, 5.0, 1.0) == 1


def test_limit_below_range_min_counts_nothing():
    assert count_near([0.1, 0.2], 0.1, 5.0, 0.05) == 0


@pytest.mark.parametrize('limit', [0.41, 0.81, 1.1])
def test_float32_range_equal_to_limit_counts(limit):
    # LaserScan.ranges are float32: float32(0.81) is slightly above the double 0.81.
    stored = array.array('f', [limit])[0]
    assert stored != limit
    assert count_near([stored], 0.0, 10.0, limit) == 1


def test_next_float32_above_limit_not_counted():
    stored = array.array('f', [0.81])[0]
    above = math.nextafter(stored, math.inf)
    above32 = array.array('f', [above])[0]
    while above32 <= stored:
        above = math.nextafter(above, math.inf)
        above32 = array.array('f', [above])[0]
    assert count_near([above32], 0.0, 10.0, 0.81) == 0


def test_huge_limit_does_not_overflow():
    assert count_near([0.5], 0.0, 10.0, 1e300) == 1
