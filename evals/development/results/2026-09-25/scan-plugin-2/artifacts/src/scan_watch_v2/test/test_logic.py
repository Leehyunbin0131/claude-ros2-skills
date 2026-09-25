import array
import math

from scan_watch_v2.logic import count_near


def f32(values):
    # rclpy delivers LaserScan.ranges as array('f'), i.e. float32 values.
    return array.array('f', values)


def test_empty_scan_is_zero():
    assert count_near([], 0.1, 10.0, 0.42) == 0
    assert count_near(f32([]), 0.1, 10.0, 0.42) == 0


def test_non_finite_ranges_are_ignored():
    ranges = f32([math.inf, -math.inf, math.nan, 0.3])
    assert count_near(ranges, 0.0, math.inf, 100.0) == 1


def test_ranges_outside_sensor_bounds_are_ignored():
    # 0.05 is below range_min, 12.0 above range_max.
    assert count_near(f32([0.05, 0.2, 12.0]), 0.1, 10.0, 100.0) == 1


def test_sensor_bounds_are_inclusive():
    rmin, rmax = f32([0.12, 3.5])
    assert count_near(f32([0.12, 3.5]), rmin, rmax, 100.0) == 2


def test_limit_is_inclusive():
    assert count_near(f32([0.3, 0.42, 0.43]), 0.1, 10.0, 0.42) == 2
    assert count_near(f32([0.82, 0.83]), 0.1, 10.0, 0.82) == 1


def test_limit_inclusive_where_float32_rounds_up():
    # float32(0.1) > 0.1 as a double; the reading should still be at the limit.
    assert array.array('f', [0.1])[0] > 0.1
    assert count_near(f32([0.1]), 0.0, 10.0, 0.1) == 1


def test_limit_below_range_min_counts_nothing():
    assert count_near(f32([0.2, 0.3]), 0.2, 10.0, 0.1) == 0


def test_mixed_scan():
    ranges = f32([0.05, 0.3, 0.42, 0.5, 0.7, 0.82, 0.9, math.inf, math.nan])
    assert count_near(ranges, 0.1, 10.0, 0.42) == 2
    assert count_near(ranges, 0.1, 10.0, 0.82) == 5


def test_integer_and_huge_limit():
    assert count_near(f32([0.5, 1.0, 1.5]), 0.1, 10.0, 1) == 2
    assert count_near(f32([0.5, 9.0]), 0.1, 10.0, 1e300) == 2
