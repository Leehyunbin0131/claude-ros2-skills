import math

from range_interfaces.msg import RangeReading

from range_py_monitor.conversion import normalize


def test_valid_reading_returns_metres():
    msg = RangeReading()
    msg.distance_m = 2.5
    msg.valid = True
    assert normalize(msg) == 2.5


def test_invalid_reading_returns_nan():
    msg = RangeReading()
    msg.distance_m = 2.5
    msg.valid = False
    assert math.isnan(normalize(msg))
