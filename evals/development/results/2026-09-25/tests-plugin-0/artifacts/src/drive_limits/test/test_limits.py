import pytest
from drive_limits.limits import limit_speeds


@pytest.mark.parametrize('left,right,cap,expected', [
    (2., 1., 1., (1., .5)),      # forward, left wheel over the limit
    (1., 3., 1.5, (.5, 1.5)),    # forward, right wheel over the limit
    (4., 4., 2., (2., 2.)),      # straight forward
    (-1., -2., 1., (-.5, -1.)),  # reverse
    (-3., -1.5, 1., (-1., -.5)),
    (2., -1., 1., (1., -.5)),    # mixed sign (turning in place / pivot)
    (-1., 4., 2., (-.5, 2.)),
    (0., 4., 2., (0., 2.)),      # one wheel stopped
])
def test_over_limit_scales_both_by_same_factor(left, right, cap, expected):
    result = limit_speeds(left, right, cap)
    assert result == pytest.approx(expected)
    # Ratio and signs preserved, and the faster wheel sits exactly at the cap.
    assert result[0] * right == pytest.approx(result[1] * left)
    assert [x > 0 for x in result] == [x > 0 for x in (left, right)]
    assert [x < 0 for x in result] == [x < 0 for x in (left, right)]
    assert max(abs(result[0]), abs(result[1])) == pytest.approx(cap)


@pytest.mark.parametrize('left,right,cap', [
    (.2, -.3, 1.),   # mixed sign in range
    (.5, .25, 1.),   # forward in range
    (-.7, -.1, 1.),  # reverse in range
    (1., -1., 1.),   # exactly at the limit
    (-2., 2., 2.),
])
def test_in_range_unchanged(left, right, cap):
    assert limit_speeds(left, right, cap) == (left, right)


@pytest.mark.parametrize('cap', [.1, 1., 5.])
def test_zero_unchanged(cap):
    assert limit_speeds(0., 0., cap) == (0., 0.)
