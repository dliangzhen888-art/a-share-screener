"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import STATIC_DIR, TEMPLATES_DIR
from app.db import initialize_database
from app.market.tencent import SUPPORTED_CODES, fetch_tencent_quote, normalize_code


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="A股短线筛选器", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


def unavailable_quote(code: str) -> dict[str, object]:
    return {
        "code": code,
        "name": None,
        "last_price": None,
        "pct_change": None,
        "turnover_amount": None,
        "turnover_rate": None,
        "volume_ratio": None,
        "float_market_cap": None,
        "total_market_cap": None,
        "quote_time": None,
        "source": "tencent",
        "status": "unavailable",
    }


@app.get("/api/quote/{code}")
def quote(code: str) -> dict[str, object]:
    if normalize_code(code) is None:
        return unavailable_quote(code)
    result = fetch_tencent_quote(code)
    return result.to_dict() if result is not None else unavailable_quote(code)


@app.get("/api/debug/tencent-benchmarks")
def tencent_benchmarks() -> list[dict[str, object]]:
    return [quote(code) for code in SUPPORTED_CODES]
