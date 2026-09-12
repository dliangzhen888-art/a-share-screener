"""沪深主板股票池 provider；提供代码、名称和上市日期。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


UNIVERSE_URL = "https://push2.eastmoney.com/api/qt/clist/get"
MAIN_BOARD_PREFIXES = ("000", "001", "002", "600", "601", "603", "605")


@dataclass(frozen=True, slots=True)
class Stock:
    code: str
    name: str
    listing_date: date


def is_main_board(code: str) -> bool:
    return len(code) == 6 and code.isdigit() and code.startswith(MAIN_BOARD_PREFIXES)


def is_excluded_name(name: str) -> bool:
    normalized = name.upper().replace(" ", "")
    return "ST" in normalized or "退" in normalized


def parse_universe(payload: bytes | str) -> list[Stock] | None:
    try:
        data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
        rows = data["data"]["diff"]
        stocks: list[Stock] = []
        for row in rows:
            code, name, raw_date = str(row["f12"]), str(row["f14"]), str(row["f26"])
            if is_main_board(code) and not is_excluded_name(name):
                stocks.append(Stock(code, name, datetime.strptime(raw_date, "%Y%m%d").date()))
        return stocks
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def fetch_universe(timeout: float = 10.0) -> list[Stock] | None:
    params = {
        "pn": 1,
        "pz": 6000,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23",
        "fields": "f12,f14,f26",
    }
    request = Request(f"{UNIVERSE_URL}?{urlencode(params)}", headers={"User-Agent": "a-share-screener/3.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return parse_universe(response.read())
    except (HTTPError, URLError, OSError, TimeoutError):
        return None
