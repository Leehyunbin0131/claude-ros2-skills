def limit_speeds(left, right, max_speed):
    """Scale both wheel speeds by one factor so neither exceeds max_speed.

    Preserves the left:right ratio (and so the turning curvature) and signs.
    Speeds already within [-max_speed, max_speed] are returned unchanged.
    """
    peak = max(abs(left), abs(right))
    if peak <= max_speed:
        return left, right
    scale = max_speed / peak
    return left * scale, right * scale
