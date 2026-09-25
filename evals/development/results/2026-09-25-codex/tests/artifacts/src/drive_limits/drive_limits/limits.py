def limit_speeds(left, right, max_speed):
    """Preserve the wheel-speed ratio for finite speeds and a positive limit."""
    peak = max(abs(left), abs(right))
    if peak <= max_speed:
        return left, right
    scale = max_speed / peak
    return left * scale, right * scale
