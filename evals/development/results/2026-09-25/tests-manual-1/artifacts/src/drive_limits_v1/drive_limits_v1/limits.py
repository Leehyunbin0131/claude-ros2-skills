def limit_speeds(left, right, max_speed):
    """Scale both wheel speeds by one factor so neither exceeds max_speed.

    Preserves the left:right ratio and signs, so a turn keeps its curvature.
    Speeds already within [-max_speed, max_speed] are returned unchanged.
    """
    peak = max(abs(left), abs(right))
    if peak <= max_speed:
        return left, right
    # Dividing first makes the dominant wheel land exactly on +/-max_speed.
    return left / peak * max_speed, right / peak * max_speed
