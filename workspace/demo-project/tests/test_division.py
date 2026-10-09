import pytest

from src.division import division


def test_division_returns_quotient():
    assert division(10, 2) == 5


def test_division_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        division(10, 0)