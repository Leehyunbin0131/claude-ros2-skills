import array
import math

from scan_watch_v3.logic import count_near

INF = math.inf
NAN = math.nan


def f32(values):
    """Ranges as rclpy delivers them: float32 values."""
    return array.array('f', values)


def test_empty_scan_is_zero():
    assert count_near(f32([]), 0.1, 10.0, 0.43) == 0


def test_counts_only_at_or_below_limit():
    assert count_near(f32([0.2, 0.3, 0.5, 0.9]), 0.1, 10.0, 0.43) == 2


def test_non_finite_ranges_are_ignored():
    assert count_near(f32([NAN, INF, -INF, 0.3]), 0.0, INF, INF) == 1


def test_ranges_outside_sensor_bounds_are_ignored():
    # 0.05 < range_min, 0.8 > range_max, even though both are <= limit.
    assert count_near(f32([0.05, 0.3, 0.8]), 0.1, 0.5, 1.0) == 1


def test_bounds_and_limit_are_inclusive():
    ranges = f32([0.1, 0.43, 0.5])
    assert count_near(ranges, ranges[0], ranges[2], 0.5) == 3
    # A float32 reading of 0.43 is counted against a 0.43 limit.
    assert count_near(ranges, ranges[0], ranges[2], 0.43) == 2


def test_limit_below_range_min_counts_nothing():
    assert count_near(f32([0.2, 0.3]), 0.2, 10.0, 0.1) == 0


def test_integer_and_huge_limits():
    assert count_near(f32([0.5, 1.0, 1.5]), 0.0, 10.0, 1) == 2
    assert count_near(f32([0.5, 9.0]), 0.0, 10.0, 1e300) == 2
