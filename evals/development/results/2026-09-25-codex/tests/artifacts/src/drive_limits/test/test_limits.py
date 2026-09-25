import pytest
from drive_limits.limits import limit_speeds

@pytest.mark.parametrize('left,right,cap,expected', [
    pytest.param(2., 1., 1., (1., .5), id='forward'),
    pytest.param(-1., -2., 1., (-.5, -1.), id='reverse'),
    pytest.param(2., -1., 1., (1., -.5), id='mixed-sign'),
    pytest.param(-2., 4., 2., (-1., 2.), id='mixed-sign-right-leading'),
    pytest.param(0., 0., 1., (0., 0.), id='zero'),
    pytest.param(.2, -.3, 1., (.2, -.3), id='in-range'),
    pytest.param(1., -.5, 1., (1., -.5), id='at-limit'),
    pytest.param(0., 4., 2., (0., 2.), id='one-zero'),
    pytest.param(4., 2., 1., (1., .5), id='both-over-limit'),
])
def test_ratio(left, right, cap, expected):
    result = limit_speeds(left, right, cap)
    assert result == pytest.approx(expected)
    if max(abs(left), abs(right)) <= cap:
        assert result == (left, right)
