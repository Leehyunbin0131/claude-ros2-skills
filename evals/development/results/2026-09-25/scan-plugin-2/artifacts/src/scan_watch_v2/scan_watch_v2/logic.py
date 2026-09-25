import math
import struct


def as_float32(value):
    """Round a Python float to the nearest float32, as LaserScan fields are stored."""
    value = float(value)
    if not math.isfinite(value):
        return value
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def count_near(ranges, range_min, range_max, limit):
    """Count finite ranges in the inclusive [range_min, range_max] that are <= limit.

    LaserScan ranges and bounds are float32, so the limit is compared at float32
    precision: a reading of 0.1 is counted with limit 0.1 even though
    float32(0.1) is slightly greater than the double 0.1.
    """
    lo = float(range_min)
    hi = float(range_max)
    limit = as_float32(limit)
    return sum(
        1 for r in ranges
        if math.isfinite(r) and lo <= r <= hi and r <= limit
    )
