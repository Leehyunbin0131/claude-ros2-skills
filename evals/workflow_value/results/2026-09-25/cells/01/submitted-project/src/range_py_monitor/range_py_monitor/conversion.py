"""Public conversion helper shared by the node and downstream tools."""
import math


def normalize(msg):
    """Return the distance in metres, or NaN if the reading is not valid."""
    if not msg.valid:
        return math.nan
    return msg.distance_m
