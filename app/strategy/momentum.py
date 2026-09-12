"""完整的两阶段动量前置筛选。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from time import perf_counter
from typing import Callable

from app.market.history import DailyBar
from app.market.tencent import TencentQuote
from app.market.universe import Stock, is_excluded_name, is_main_board
from app.strategy.indicators import is_ma20_rising, moving_average, wilder_rsi


@dataclass(frozen=True, slots=True)
class Candidate:
    code: str
    name: str
    last_price: float
    pct_change: float
    turnover_rate: float
    volume_ratio: float
    turnover_amount: float
    total_market_cap: float
    listing_date: str
    listing_days: int
    avg_amount_20d: float
    return_5d: float
    ma5: float
    ma10: float
    ma20: float
    ma20_rising: bool
    rsi14: float
    ma_bullish: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def passes_stage1(stock: Stock, quote: TencentQuote, today: date) -> bool:
    listing_days = (today - stock.listing_date).days
    return (
        stock.code == quote.code
        and is_main_board(stock.code)
        and not is_excluded_name(stock.name)
        and not is_excluded_name(quote.name)
        and listing_days > 120
        and quote.total_market_cap > 8_000_000_000
        and quote.turnover_amount > 500_000_000
        and 1 < quote.pct_change < 7
        and 3 < quote.turnover_rate < 12
        and 1.1 < quote.volume_ratio < 2.5
    )


def passes_stage2_values(
    *, last_price: float, avg_amount_20d: float, return_5d: float,
    ma5: float, ma10: float, ma20: float, ma20_rising: bool, rsi14: float,
) -> bool:
    """集中表达所有严格开区间和趋势条件，便于边界审计。"""
    return (
        avg_amount_20d > 300_000_000
        and 2 < return_5d < 18
        and last_price > ma20
        and ma5 > ma10 > ma20
        and ma20_rising
        and 50 < rsi14 < 80
    )


def evaluate_stage2(stock: Stock, quote: TencentQuote, bars: list[DailyBar], today: date) -> Candidate | None:
    if len(bars) < 23 or any(bar.close is None or bar.amount is None for bar in bars):
        return None
    closes = [bar.close for bar in bars]
    amounts = [bar.amount for bar in bars]
    quote_day = quote.quote_time[:8]
    if bars[-1].date.replace("-", "") == quote_day:
        closes[-1] = quote.last_price
        amounts[-1] = quote.turnover_amount
    else:
        closes.append(quote.last_price)
        amounts.append(quote.turnover_amount)
    ma5, ma10, ma20 = (moving_average(closes, period) for period in (5, 10, 20))
    rsi14 = wilder_rsi(closes)
    avg_amount = moving_average(amounts, 20)
    return_5d = (quote.last_price / closes[-6] - 1) * 100 if len(closes) >= 6 else None
    rising = is_ma20_rising(closes)
    if None in (ma5, ma10, ma20, rsi14, avg_amount, return_5d):
        return None
    assert ma5 is not None and ma10 is not None and ma20 is not None
    assert rsi14 is not None and avg_amount is not None and return_5d is not None
    bullish = ma5 > ma10 > ma20
    if not passes_stage2_values(
        last_price=quote.last_price, avg_amount_20d=avg_amount, return_5d=return_5d,
        ma5=ma5, ma10=ma10, ma20=ma20, ma20_rising=rising, rsi14=rsi14,
    ):
        return None
    return Candidate(
        code=stock.code, name=quote.name, last_price=quote.last_price,
        pct_change=quote.pct_change, turnover_rate=quote.turnover_rate,
        volume_ratio=quote.volume_ratio, turnover_amount=quote.turnover_amount,
        total_market_cap=quote.total_market_cap, listing_date=stock.listing_date.isoformat(),
        listing_days=(today - stock.listing_date).days, avg_amount_20d=avg_amount,
        return_5d=return_5d, ma5=ma5, ma10=ma10, ma20=ma20,
        ma20_rising=rising, rsi14=rsi14, ma_bullish=bullish,
    )


def run_screen(
    stocks: list[Stock], quotes: dict[str, TencentQuote],
    history_fetcher: Callable[[str], list[DailyBar] | None], today: date,
    failed_batches: int = 0,
) -> dict[str, object]:
    started = perf_counter()
    stage1 = [stock for stock in stocks if (quote := quotes.get(stock.code)) and passes_stage1(stock, quote, today)]
    candidates: list[Candidate] = []
    history_requests = 0
    for stock in stage1:
        history_requests += 1
        bars = history_fetcher(stock.code)
        quote = quotes[stock.code]
        if bars is not None and (candidate := evaluate_stage2(stock, quote, bars, today)) is not None:
            candidates.append(candidate)
    candidates.sort(key=lambda item: (-item.return_5d, -item.turnover_amount))
    return {
        "results": [candidate.to_dict() for candidate in candidates],
        "stats": {"universe_total": len(stocks), "stage1_passed": len(stage1),
                  "stage2_passed": len(candidates), "elapsed_seconds": perf_counter() - started,
                  "failed_batches": failed_batches, "history_requests": history_requests},
    }
