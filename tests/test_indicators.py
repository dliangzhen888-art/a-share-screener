import pytest

from app.strategy.indicators import is_ma20_rising, moving_average, wilder_rsi


def test_moving_averages_and_rising() -> None:
    closes = [float(value) for value in range(1, 41)]
    assert moving_average(closes, 5) == 38
    assert moving_average(closes, 10) == 35.5
    assert moving_average(closes, 20) == 30.5
    assert is_ma20_rising(closes)
    assert not is_ma20_rising(list(reversed(closes)))


def test_ma20_rising_requires_three_day_comparison_history() -> None:
    assert not is_ma20_rising([100.0] * 22)
    closes = [100.0] * 20 + [101.0, 99.0, 102.0]
    assert is_ma20_rising(closes)


def test_wilder_rsi_boundaries() -> None:
    fifty = [100.0]
    eighty = [100.0]
    for index in range(14):
        fifty.append(fifty[-1] + (1 if index % 2 == 0 else -1))
        eighty.append(eighty[-1] + (4 if index % 2 == 0 else -1))
    assert wilder_rsi(fifty) == pytest.approx(50)
    assert wilder_rsi(eighty) == pytest.approx(80)


def test_rsi_missing_history_is_none() -> None:
    assert wilder_rsi([100.0] * 14) is None
