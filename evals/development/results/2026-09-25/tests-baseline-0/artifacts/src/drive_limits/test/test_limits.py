import pytest
from drive_limits.limits import limit_speeds


@pytest.mark.parametrize('left,right,cap,expected', [
    pytest.param(2., 1., 1., (1., .5), id='forward'),
    pytest.param(3., 1.5, 1.5, (1.5, .75), id='forward-right-under-cap'),
    pytest.param(-1., -2., 1., (-.5, -1.), id='reverse'),
    pytest.param(-4., -1., 2., (-2., -.5), id='reverse-left-dominant'),
    pytest.param(2., -1., 1., (1., -.5), id='mixed-sign'),
    pytest.param(-.5, 4., 2., (-.25, 2.), id='mixed-sign-right-dominant'),
    pytest.param(0., 4., 2., (0., 2.), id='pivot-one-wheel-zero'),
])
def test_scales_both_wheels_by_same_factor(left, right, cap, expected):
    out = limit_speeds(left, right, cap)
    assert out == pytest.approx(expected)
    assert max(abs(out[0]), abs(out[1])) == pytest.approx(cap)
    # Curvature is preserved: out is a positive multiple of the input.
    assert out[0] * right == pytest.approx(out[1] * left)
    assert (out[0] > 0) == (left > 0) and (out[0] < 0) == (left < 0)
    assert (out[1] > 0) == (right > 0) and (out[1] < 0) == (right < 0)


@pytest.mark.parametrize('left,right,cap', [
    pytest.param(.2, -.3, 1., id='in-range-mixed'),
    pytest.param(.7, .4, 1., id='in-range-forward'),
    pytest.param(-1., -.25, 1., id='at-limit'),
    pytest.param(0., 0., 1., id='zero'),
])
def test_in_range_unchanged(left, right, cap):
    assert limit_speeds(left, right, cap) == (left, right)
