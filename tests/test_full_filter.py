from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.market.history import DailyBar
from app.market.tencent import TencentQuote
from app.market.universe import Stock, is_excluded_name, is_main_board
from app.strategy.momentum import evaluate_stage2, passes_stage1, passes_stage2_values, run_screen


TODAY = date(2026, 9, 12)
STOCK = Stock("600519", "贵州茅台", TODAY - timedelta(days=1000))


def quote(**changes: object) -> TencentQuote:
    base = TencentQuote(
        code="600519", name="贵州茅台", last_price=121.2, previous_close=118,
        open_price=118.5, volume=10_000_000, quote_time="20260912150000",
        pct_change=3, high_price=121, low_price=118, turnover_amount=700_000_000,
        turnover_rate=5, float_market_cap=900_000_000_000,
        total_market_cap=1_000_000_000_000, limit_up=130, limit_down=106,
        volume_ratio=1.5,
    )
    return replace(base, **changes)


def bars(amount: float = 400_000_000) -> list[DailyBar]:
    closes = [100 + index * 0.5 + (1 if index % 2 else 0) for index in range(40)]
    return [DailyBar((TODAY - timedelta(days=40 - index)).isoformat(), close, amount)
            for index, close in enumerate(closes)]


@pytest.mark.parametrize("field,value", [
    ("pct_change", 1), ("pct_change", 7),
    ("turnover_rate", 3), ("turnover_rate", 12),
    ("volume_ratio", 1.1), ("volume_ratio", 2.5),
    ("total_market_cap", 8_000_000_000),
    ("turnover_amount", 500_000_000),
])
def test_stage1_strict_boundaries(field: str, value: float) -> None:
    assert not passes_stage1(STOCK, quote(**{field: value}), TODAY)


def test_stock_scope_name_and_listing_filters() -> None:
    assert is_main_board("000001") and is_main_board("605001")
    assert not is_main_board("300001") and not is_main_board("688001")
    assert is_excluded_name("*ST示例") and is_excluded_name("退市示例")
    young = replace(STOCK, listing_date=TODAY - timedelta(days=120))
    assert not passes_stage1(young, quote(), TODAY)


def test_stage2_complete_pass_and_fields() -> None:
    candidate = evaluate_stage2(STOCK, quote(), bars(), TODAY)
    assert candidate is not None
    assert candidate.ma5 > candidate.ma10 > candidate.ma20
    assert candidate.ma20_rising
    assert 50 < candidate.rsi14 < 80
    assert 2 < candidate.return_5d < 18


def test_average_amount_boundary() -> None:
    assert evaluate_stage2(STOCK, quote(turnover_amount=300_000_000), bars(300_000_000), TODAY) is None


def test_close_must_exceed_ma20_and_ma_must_be_bullish() -> None:
    assert evaluate_stage2(STOCK, quote(last_price=90), bars(), TODAY) is None
    falling = [DailyBar(bar.date, 150 - index, bar.amount) for index, bar in enumerate(bars())]
    assert evaluate_stage2(STOCK, quote(), falling, TODAY) is None


def test_return_5d_strict_boundaries() -> None:
    history = bars()
    base = history[-6].close
    assert evaluate_stage2(STOCK, quote(last_price=base * 1.02), history, TODAY) is None
    assert evaluate_stage2(STOCK, quote(last_price=base * 1.18), history, TODAY) is None


@pytest.mark.parametrize("field,value", [
    ("return_5d", 2), ("return_5d", 18), ("avg_amount_20d", 300_000_000),
    ("last_price", 100), ("ma5", 102), ("ma10", 100),
    ("rsi14", 50), ("rsi14", 80), ("ma20_rising", False),
])
def test_stage2_metric_boundaries(field: str, value: object) -> None:
    metrics = {"last_price": 110, "avg_amount_20d": 400_000_000, "return_5d": 5,
               "ma5": 105, "ma10": 102, "ma20": 100, "ma20_rising": True, "rsi14": 65}
    metrics[field] = value
    assert not passes_stage2_values(**metrics)


def test_null_or_missing_history_fails_closed() -> None:
    assert evaluate_stage2(STOCK, quote(), bars()[:19], TODAY) is None
    corrupt = bars()
    corrupt[-1] = DailyBar(corrupt[-1].date, None, corrupt[-1].amount)  # type: ignore[arg-type]
    assert evaluate_stage2(STOCK, quote(), corrupt, TODAY) is None
    result = run_screen([STOCK], {STOCK.code: quote()}, lambda _: None, TODAY)
    assert result["stats"]["stage1_passed"] == 1
    assert result["stats"]["stage2_passed"] == 0
    assert result["stats"]["history_requests"] == 1


def test_results_sort_by_return_then_amount() -> None:
    first = STOCK
    second = Stock("600001", "示例二", STOCK.listing_date)
    second_quote = replace(quote(), code="600001", name="示例二", turnover_amount=800_000_000)
    result = run_screen([first, second], {first.code: quote(), second.code: second_quote}, lambda _: bars(), TODAY)
    assert [item["code"] for item in result["results"]] == ["600001", "600519"]
