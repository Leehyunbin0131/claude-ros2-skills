def limit_speeds(left, right, max_speed):
    """Limit wheel speeds to +/-max_speed while preserving the left:right ratio.

    If the larger magnitude exceeds max_speed, both speeds are scaled by the
    same factor so the turning curvature is unchanged; otherwise both are
    returned as-is.
    """
    peak = max(abs(left), abs(right))
    if peak <= max_speed:
        return left, right
    scale = max_speed / peak
    return left * scale, right * scale
