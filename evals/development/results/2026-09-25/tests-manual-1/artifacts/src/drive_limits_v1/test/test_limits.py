import pytest
from drive_limits_v1.limits import limit_speeds


@pytest.mark.parametrize('left,right,cap,expected', [
    pytest.param(2., 1., 1., (1., .5), id='forward'),
    pytest.param(-1., -2., 1., (-.5, -1.), id='reverse'),
    pytest.param(2., -1., 1., (1., -.5), id='mixed_sign'),
    pytest.param(-3., 1.5, 1., (-1., .5), id='mixed_sign_left_dominant'),
    pytest.param(0., 4., 2., (0., 2.), id='pivot_one_wheel_zero'),
])
def test_over_limit_scales_both_wheels_equally(left, right, cap, expected):
    assert limit_speeds(left, right, cap) == pytest.approx(expected)


@pytest.mark.parametrize('left,right,cap', [
    pytest.param(.2, -.3, 1., id='in_range'),
    pytest.param(1., -1., 1., id='exactly_at_limit'),
    pytest.param(-.7, -.7, 1., id='in_range_reverse'),
    pytest.param(0., 0., 1., id='zero'),
])
def test_in_range_is_unchanged(left, right, cap):
    assert limit_speeds(left, right, cap) == (left, right)


@pytest.mark.parametrize('left,right,cap', [
    (2., 1., 1.), (-1., -2., 1.), (2., -1., 1.), (7.3, 0.1, 0.4),
    (-5., 3., 2.5), (1e6, -3e5, 1.2),
])
def test_ratio_signs_and_limit_preserved(left, right, cap):
    out_left, out_right = limit_speeds(left, right, cap)
    assert max(abs(out_left), abs(out_right)) == pytest.approx(cap)
    assert max(abs(out_left), abs(out_right)) <= cap
    assert (out_left > 0) == (left > 0) and (out_left < 0) == (left < 0)
    assert (out_right > 0) == (right > 0) and (out_right < 0) == (right < 0)
    assert out_left * right == pytest.approx(out_right * left)
