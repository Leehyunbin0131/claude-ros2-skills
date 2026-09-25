import math
from array import array

from scan_watch.logic import count_near

INF = math.inf
NAN = math.nan


def test_empty_scan_is_zero():
    assert count_near([], 0.1, 10.0, 0.4) == 0
    assert count_near(array('f'), 0.1, 10.0, 0.4) == 0


def test_non_finite_ranges_ignored():
    assert count_near([NAN, INF, -INF, 0.2], 0.0, 10.0, 100.0) == 1


def test_non_finite_ignored_even_with_infinite_bounds_and_limit():
    assert count_near([INF, -INF, NAN, 0.3], -INF, INF, INF) == 1


def test_range_bounds_are_inclusive():
    # range_min and range_max themselves count; values outside do not.
    assert count_near([0.05, 0.1, 0.3, 0.5, 0.6], 0.1, 0.5, 10.0) == 3


def test_limit_is_inclusive():
    assert count_near([0.39, 0.4, 0.41], 0.0, 10.0, 0.4) == 2


def test_limit_inclusive_at_float32_precision():
    # rclpy delivers LaserScan.ranges as float32: 0.4 arrives as
    # 0.4000000059604645, which must still count against limit 0.4.
    ranges = array('f', [0.4, 0.8])
    assert ranges[0] > 0.4
    assert count_near(ranges, 0.0, 10.0, 0.4) == 1
    assert count_near(ranges, 0.0, 10.0, 0.8) == 2


def test_below_range_min_not_counted_even_if_below_limit():
    assert count_near([0.01, 0.02], 0.05, 10.0, 0.4) == 0


def test_limit_above_range_max_capped_by_range_max():
    assert count_near([1.0, 2.0, 3.0], 0.0, 2.0, 5.0) == 2


def test_negative_limit_counts_nothing():
    assert count_near([0.1, 0.2], 0.0, 10.0, -1.0) == 0


def test_huge_limit_saturates_instead_of_overflowing():
    assert count_near([0.1, 5.0], 0.0, 10.0, 1e300) == 2
