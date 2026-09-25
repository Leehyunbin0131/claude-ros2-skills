import numpy as np


def count_near(ranges, range_min, range_max, limit):
    """Count finite ranges in the inclusive [range_min, range_max] that are <= limit.

    Everything is compared at float32, the precision of LaserScan fields, so a
    range published as the same decimal value as the limit (e.g. 0.81) counts.
    """
    with np.errstate(over='ignore'):
        r = np.asarray(ranges, dtype=np.float32)
        lo, hi, lim = np.float32(range_min), np.float32(range_max), np.float32(limit)
    mask = np.isfinite(r) & (r >= lo) & (r <= hi) & (r <= lim)
    return int(np.count_nonzero(mask))
