from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
import yfinance as yf

from briefing.config import Settings

UA = {"User-Agent": "SignalDeskMorningBrief/1.0"}

# Yahoo symbols
YF_SYMBOLS = {
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "SPX": "^GSPC",
}


def _pct(prev: float, last: float) -> float | None:
    if prev == 0:
        return None
    return ((last - prev) / prev) * 100


def fetch_yfinance_snapshot() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, symbol in YF_SYMBOLS.items():
        try:
            hist = yf.Ticker(symbol).history(period="10d", interval="1d")
            if hist is None or hist.empty:
                out[name] = {"symbol": symbol, "error": "no data"}
                continue
            closes = hist["Close"].dropna()
            last = float(closes.iloc[-1])
            prev = float(closes.iloc[-2]) if len(closes) > 1 else last
            out[name] = {
                "symbol": symbol,
                "last": round(last, 4),
                "prev_close": round(prev, 4),
                "chg_pct": round(_pct(prev, last) or 0.0, 3),
            }
        except Exception as exc:  # noqa: BLE001
            out[name] = {"symbol": symbol, "error": str(exc)}
    return out


def fetch_fred_series(api_key: str, series_id: str) -> dict[str, Any] | None:
    if not api_key:
        return None
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    try:
        res = requests.get(url, params=params, headers=UA, timeout=20)
        res.raise_for_status()
        obs = [
            o
            for o in res.json().get("observations", [])
            if o.get("value") not in (None, ".")
        ]
        if not obs:
            return None
        latest = float(obs[0]["value"])
        prev = float(obs[1]["value"]) if len(obs) > 1 else latest
        return {
            "series_id": series_id,
            "date": obs[0].get("date"),
            "last": latest,
            "prev": prev,
            "chg": round(latest - prev, 4),
        }
    except Exception as exc:  # noqa: BLE001
        return {"series_id": series_id, "error": str(exc)}


def collect_macro(settings: Settings) -> dict[str, Any]:
    yf_data = fetch_yfinance_snapshot()
    fred: dict[str, Any] = {}
    if settings.fred_api_key:
        # DFF: effective federal funds rate, DTWEXBGS: broad USD index alternative
        fred["FEDFUNDS"] = fetch_fred_series(settings.fred_api_key, "DFF")
        fred["DGS10"] = fetch_fred_series(settings.fred_api_key, "DGS10")
        fred["DTWEXBGS"] = fetch_fred_series(settings.fred_api_key, "DTWEXBGS")

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "yahoo": yf_data,
        "fred": fred,
        "notes": [
            "연준 관련은 현직 의장/FOMC 커뮤니케이션·금리 경로 중심으로 요약 (특정 전임자 고정 금지).",
            "DXY=DX-Y.NYB, US10Y=^TNX, S&P500=^GSPC (Yahoo).",
        ],
    }
