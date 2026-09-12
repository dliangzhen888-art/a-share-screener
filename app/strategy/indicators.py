"""不依赖 pandas/numpy 的价格指标。"""

from __future__ import annotations


def moving_average(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period or any(value is None for value in values):
        return None
    return sum(values[-period:]) / period


def is_ma20_rising(closes: list[float], lookback: int = 3) -> bool:
    """以今日 MA20 和若干交易日前 MA20 比较，避免单日噪声。"""
    if lookback < 1 or len(closes) < 20 + lookback:
        return False
    today = moving_average(closes, 20)
    earlier = moving_average(closes[:-lookback], 20)
    return today is not None and earlier is not None and today > earlier


def wilder_rsi(closes: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(closes) < period + 1:
        return None
    changes = [current - previous for previous, current in zip(closes, closes[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - (100 / (1 + avg_gain / avg_loss))
