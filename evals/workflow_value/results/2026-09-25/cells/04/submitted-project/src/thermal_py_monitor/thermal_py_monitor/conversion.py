"""Public conversion helper shared by the node and downstream tools."""

import math


def normalize(msg):
    """Return the temperature in degrees Celsius, or NaN if the reading is invalid."""
    if not msg.valid:
        return math.nan
    return msg.temperature_c
