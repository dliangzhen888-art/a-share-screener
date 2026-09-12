"""可替换的腾讯日 K 历史行情 provider。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.market.tencent import normalize_code


HISTORY_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
FALLBACK_HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


@dataclass(frozen=True, slots=True)
class DailyBar:
    date: str
    close: float
    amount: float


def parse_history(payload: bytes | str, symbol: str) -> list[DailyBar] | None:
    """解析腾讯前复权日 K；任一关键字段异常时整批关闭。"""
    try:
        document = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
        node = document["data"][symbol]
        rows = node.get("qfqday") or node.get("day")
        if not isinstance(rows, list) or len(rows) < 20:
            return None
        bars = [DailyBar(date=row[0], close=float(row[2]), amount=float(row[6])) for row in rows]
        if any(bar.close <= 0 or bar.amount < 0 or not bar.date for bar in bars):
            return None
        return bars
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def fetch_history(code: str, count: int = 40, timeout: float = 8.0) -> list[DailyBar] | None:
    symbol = normalize_code(code)
    if symbol is None:
        return None
    query = urlencode({"param": f"{symbol},day,,,{count},qfq"})
    request = Request(f"{HISTORY_URL}?{query}", headers={"User-Agent": "a-share-screener/3.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            bars = parse_history(response.read(), symbol)
            if bars is not None:
                return bars
    except (HTTPError, URLError, OSError, TimeoutError):
        pass
    return fetch_fallback_history(code, count, timeout)


def fetch_fallback_history(code: str, count: int = 40, timeout: float = 8.0) -> list[DailyBar] | None:
    """腾讯日 K 不含可靠成交额时使用独立备用 provider。"""
    symbol = normalize_code(code)
    if symbol is None:
        return None
    params = {
        "secid": f"{1 if symbol.startswith('sh') else 0}.{symbol[2:]}", "klt": 101,
        "fqt": 1, "lmt": count, "end": "20500101", "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
    }
    request = Request(f"{FALLBACK_HISTORY_URL}?{urlencode(params)}", headers={"User-Agent": "a-share-screener/3.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            document = json.loads(response.read().decode("utf-8"))
        rows = document["data"]["klines"]
        bars = [DailyBar(parts[0], float(parts[2]), float(parts[6])) for row in rows if len(parts := row.split(",")) >= 7]
        if len(bars) < 20 or any(bar.close <= 0 or bar.amount < 0 for bar in bars):
            return None
        return bars
    except (HTTPError, URLError, OSError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
