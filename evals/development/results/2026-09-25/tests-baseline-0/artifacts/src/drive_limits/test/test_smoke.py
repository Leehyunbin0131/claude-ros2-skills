def test_public_import():
    from drive_limits.limits import limit_speeds
    assert callable(limit_speeds)
