import math

from power_interfaces.msg import PowerReading

from power_py_monitor.conversion import normalize


def test_returns_watts_when_valid():
    msg = PowerReading()
    msg.power_w = 12.5
    msg.valid = True
    assert normalize(msg) == 12.5


def test_returns_nan_when_invalid():
    msg = PowerReading()
    msg.power_w = 12.5
    msg.valid = False
    assert math.isnan(normalize(msg))
