import math
import struct


def _as_float32(value):
    """Round a Python float to the nearest float32, as LaserScan fields are stored."""
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError:
        # Beyond the float32 range: no finite float32 range can exceed it anyway.
        return value


def count_near(ranges, range_min, range_max, limit):
    """Count finite ranges inside the inclusive [range_min, range_max] and <= limit.

    LaserScan ranges are float32, so the limit is compared at float32 precision:
    a reading published as 0.43 is counted when the limit is 0.43.
    """
    limit = _as_float32(float(limit))
    return sum(
        1 for r in ranges
        if math.isfinite(r) and range_min <= r <= range_max and r <= limit
    )
