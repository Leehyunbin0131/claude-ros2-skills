from range_interfaces.msg import RangeReading


def test_fields():
    assert RangeReading.get_fields_and_field_types() == {
        'distance_m': 'double',
        'valid': 'boolean',
    }


def test_defaults_to_invalid():
    assert RangeReading().valid is False
