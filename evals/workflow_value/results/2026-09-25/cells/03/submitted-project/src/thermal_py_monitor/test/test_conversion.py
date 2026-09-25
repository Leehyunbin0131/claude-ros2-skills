import math

from thermal_interfaces.msg import ThermalReading

from thermal_py_monitor.conversion import normalize


def test_valid_reading_returns_degrees_celsius():
    msg = ThermalReading()
    msg.temperature_c = 21.5
    msg.valid = True
    assert normalize(msg) == 21.5


def test_invalid_reading_returns_nan():
    msg = ThermalReading()
    msg.temperature_c = 21.5
    msg.valid = False
    assert math.isnan(normalize(msg))
