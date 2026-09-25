import math
import struct


def to_float32(value):
    """Round a Python float to the nearest float32, saturating to +/-inf."""
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def count_near(ranges, range_min, range_max, limit):
    """Count finite ranges inside [range_min, range_max] and <= limit.

    LaserScan ranges are float32, so the limit is compared at float32
    precision: a reading published as 0.4 must count against limit 0.4 even
    though float32(0.4) is slightly larger than the double 0.4.
    """
    limit = to_float32(limit)
    return sum(
        1 for r in ranges
        if math.isfinite(r) and range_min <= r <= range_max and r <= limit)
