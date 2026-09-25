"""Public conversion helper shared by the node and downstream tools."""

import math


def normalize(msg):
    """Return the power in watts, or NaN if the reading is not valid."""
    if not msg.valid:
        return math.nan
    return msg.power_w
