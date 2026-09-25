import math
import struct


def _to_float32(value):
    """Round a float to single precision, the type of LaserScan range fields."""
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def count_near(ranges, range_min, range_max, limit):
    """Count finite ranges in inclusive [range_min, range_max] that are <= limit.

    The limit is compared at float32 precision so that a reading equal to the
    limit (e.g. 0.4 stored as float32 0.4000000059...) counts as "at" the limit.
    """
    limit = _to_float32(limit)
    return sum(
        1 for r in ranges
        if math.isfinite(r) and range_min <= r <= range_max and r <= limit
    )
