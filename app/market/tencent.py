"""腾讯 Web 行情接口的轻量客户端和严格解析器。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
SUPPORTED_CODES = ("600519", "000001", "002130", "002897")


@dataclass(frozen=True, slots=True)
class TencentQuote:
    code: str
    name: str
    last_price: float
    previous_close: float
    open_price: float
    volume: int
    quote_time: str
    pct_change: float
    high_price: float
    low_price: float
    turnover_amount: float
    turnover_rate: float
    float_market_cap: float
    total_market_cap: float
    limit_up: float
    limit_down: float
    volume_ratio: float
    source: str = "tencent"
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_code(code: str) -> str | None:
    """校验六位代码并添加腾讯接口所需的市场前缀。"""
    if len(code) == 8 and code[:2] in {"sh", "sz"}:
        bare_code = code[2:]
        expected_prefix = "sh" if bare_code.startswith("6") else "sz"
        if code[:2] != expected_prefix:
            return None
        code = bare_code
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    if code.startswith("6"):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    return None


def _number(fields: list[str], index: int) -> float:
    value = fields[index].strip()
    if not value:
        raise ValueError(f"missing field {index}")
    return float(value)


def parse_tencent_quote(raw: bytes | str, expected_code: str | None = None) -> TencentQuote | None:
    """解析单条腾讯行情；格式或合理性异常时严格返回 ``None``。"""
    try:
        text = raw.decode("gb18030") if isinstance(raw, bytes) else raw
        start = text.index('="') + 2
        end = text.index('"', start)
        fields = text[start:end].split("~")
        if len(fields) <= 49:
            return None

        name = fields[1].strip()
        code = fields[2].strip()
        quote_time = fields[30].strip()
        if not name or not quote_time or normalize_code(code) is None:
            return None
        if expected_code is not None and code != expected_code:
            return None

        last_price = _number(fields, 3)
        previous_close = _number(fields, 4)
        open_price = _number(fields, 5)
        volume_hands = _number(fields, 6)
        pct_change = _number(fields, 32)
        high_price = _number(fields, 33)
        low_price = _number(fields, 34)
        turnover_ten_thousand = _number(fields, 37)
        turnover_rate = _number(fields, 38)
        float_cap_hundred_million = _number(fields, 44)
        total_cap_hundred_million = _number(fields, 45)
        limit_up = _number(fields, 47)
        limit_down = _number(fields, 48)
        volume_ratio = _number(fields, 49)

        numbers = (
            last_price,
            previous_close,
            open_price,
            volume_hands,
            pct_change,
            high_price,
            low_price,
            turnover_ten_thousand,
            turnover_rate,
            float_cap_hundred_million,
            total_cap_hundred_million,
            limit_up,
            limit_down,
            volume_ratio,
        )
        if not (
            all(isfinite(value) for value in numbers)
            and last_price > 0
            and previous_close > 0
            and high_price >= low_price
            and 0 <= turnover_rate < 100
            and 0 <= volume_ratio < 100
            and float_cap_hundred_million > 0
            and total_cap_hundred_million > 0
            and float_cap_hundred_million <= total_cap_hundred_million * 1.2
            and turnover_ten_thousand >= 0
            and volume_hands >= 0
        ):
            return None

        return TencentQuote(
            code=code,
            name=name,
            last_price=last_price,
            previous_close=previous_close,
            open_price=open_price,
            volume=int(volume_hands * 100),
            quote_time=quote_time,
            pct_change=pct_change,
            high_price=high_price,
            low_price=low_price,
            turnover_amount=turnover_ten_thousand * 10_000,
            turnover_rate=turnover_rate,
            float_market_cap=float_cap_hundred_million * 100_000_000,
            total_market_cap=total_cap_hundred_million * 100_000_000,
            limit_up=limit_up,
            limit_down=limit_down,
            volume_ratio=volume_ratio,
        )
    except (IndexError, UnicodeDecodeError, ValueError, OverflowError):
        return None


def fetch_tencent_quote(code: str, timeout: float = 5.0) -> TencentQuote | None:
    """从腾讯读取单股实时行情；网络或解析失败时返回 ``None``。"""
    symbol = normalize_code(code)
    if symbol is None:
        return None
    request = Request(
        f"{TENCENT_QUOTE_URL}{symbol}",
        headers={"User-Agent": "a-share-screener/2.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return parse_tencent_quote(response.read(), expected_code=symbol[2:])
    except (HTTPError, URLError, OSError, TimeoutError):
        return None


def fetch_tencent_quotes(codes: list[str], batch_size: int = 50, timeout: float = 8.0) -> tuple[dict[str, TencentQuote], int]:
    """低并发顺序批量获取实时行情，并统计失败批次。"""
    quotes: dict[str, TencentQuote] = {}
    failed_batches = 0
    symbols = [symbol for code in codes if (symbol := normalize_code(code)) is not None]
    for offset in range(0, len(symbols), batch_size):
        batch = symbols[offset : offset + batch_size]
        request = Request(f"{TENCENT_QUOTE_URL}{','.join(batch)}", headers={"User-Agent": "a-share-screener/3.0"})
        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("gb18030")
            parsed = 0
            for statement in text.splitlines():
                quote = parse_tencent_quote(statement)
                if quote is not None and normalize_code(quote.code) in batch:
                    quotes[quote.code] = quote
                    parsed += 1
            if parsed == 0:
                failed_batches += 1
        except (HTTPError, URLError, OSError, TimeoutError, UnicodeDecodeError):
            failed_batches += 1
    return quotes, failed_batches
