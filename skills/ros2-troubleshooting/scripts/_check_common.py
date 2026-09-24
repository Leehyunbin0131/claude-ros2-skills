"""ROS-free validation shared by the standalone checks."""
import argparse
import math


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def nonnegative_float(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return number


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be an integer greater than zero")
    return number


def exit_code(verdict):
    return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}[verdict]


def unit_quaternion(x, y, z, w):
    """Validate a ROS orientation; normalize only small rounding errors."""
    values = (x, y, z, w)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("orientation contains non-finite values")
    norm = math.hypot(*values)
    if abs(norm - 1.0) > 0.01:
        raise ValueError("orientation quaternion is not normalized")
    return tuple(v / norm for v in values)
