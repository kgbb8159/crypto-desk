from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
import yfinance as yf
from bs4 import BeautifulSoup

from briefing.config import DEFILLAMA_PROTOCOLS

UA = {"User-Agent": "SignalDeskMorningBrief/1.0"}

PRICE_SYMBOLS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "LINK": "LINK-USD",
    "ONDO": "ONDO-USD",
    "TAO": "TAO-USD",
    "CRCL": "CRCL",
}


def _chg(hist) -> dict[str, Any]:
    closes = hist["Close"].dropna()
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2]) if len(closes) > 1 else last
    chg = ((last - prev) / prev * 100) if prev else 0.0
    return {"last": round(last, 4), "chg_pct_1d": round(chg, 3)}


GECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "LINK": "chainlink",
    "ONDO": "ondo-finance",
    "TAO": "bittensor",
}


def fetch_prices_coingecko() -> dict[str, Any]:
    ids = ",".join(GECKO_IDS.values())
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    )
    res = requests.get(url, headers=UA, timeout=20)
    res.raise_for_status()
    data = res.json()
    out: dict[str, Any] = {}
    for ticker, gid in GECKO_IDS.items():
        row = data.get(gid) or {}
        if "usd" not in row:
            out[ticker] = {"source": "coingecko", "error": "no data"}
            continue
        out[ticker] = {
            "source": "coingecko",
            "last": row["usd"],
            "chg_pct_1d": round(float(row.get("usd_24h_change") or 0), 3),
        }
    return out


def fetch_prices() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ticker, symbol in PRICE_SYMBOLS.items():
        try:
            hist = yf.Ticker(symbol).history(period="10d", interval="1d")
            if hist is None or hist.empty:
                out[ticker] = {"symbol": symbol, "error": "no data"}
                continue
            snap = _chg(hist)
            snap["symbol"] = symbol
            snap["source"] = "yahoo"
            out[ticker] = snap
        except Exception as exc:  # noqa: BLE001
            out[ticker] = {"symbol": symbol, "error": str(exc)}

    # Yahoo에 없는 TAO 등 보완
    try:
        gecko = fetch_prices_coingecko()
        for ticker, row in gecko.items():
            if ticker not in out or out[ticker].get("error"):
                out[ticker] = row
            elif ticker == "TAO":
                out[ticker] = row
    except Exception as exc:  # noqa: BLE001
        if out.get("TAO", {}).get("error"):
            out["TAO"] = {"error": f"yahoo+coingecko failed: {exc}"}
    return out


def fetch_defillama_protocol(slug: str) -> dict[str, Any]:
    url = f"https://api.llama.fi/protocol/{slug}"
    res = requests.get(url, headers=UA, timeout=25)
    res.raise_for_status()
    data = res.json()
    tvl_series = data.get("tvl") or []
    current = None
    prev = None
    if isinstance(tvl_series, list) and tvl_series:
        # list of {date, totalLiquidityUSD} or just numbers depending on endpoint
        last = tvl_series[-1]
        prev_row = tvl_series[-2] if len(tvl_series) > 1 else last
        if isinstance(last, dict):
            current = last.get("totalLiquidityUSD")
            prev = prev_row.get("totalLiquidityUSD")
        else:
            current = last
            prev = prev_row
    elif isinstance(data.get("currentChainTvls"), dict):
        current = sum(v for v in data["currentChainTvls"].values() if isinstance(v, (int, float)))
    chg = None
    if isinstance(current, (int, float)) and isinstance(prev, (int, float)) and prev:
        chg = ((current - prev) / prev) * 100
    return {
        "slug": slug,
        "name": data.get("name") or slug,
        "tvl_usd": round(float(current), 2) if isinstance(current, (int, float)) else None,
        "tvl_chg_pct_approx": round(chg, 3) if isinstance(chg, float) else None,
        "url": f"https://defillama.com/protocol/{slug}",
    }


def fetch_solana_chain_tvl() -> dict[str, Any]:
    url = "https://api.llama.fi/v2/historicalChainTvl/Solana"
    res = requests.get(url, headers=UA, timeout=25)
    res.raise_for_status()
    series = res.json()
    if not series:
        return {"chain": "Solana", "error": "empty"}
    last = series[-1]
    prev = series[-2] if len(series) > 1 else last
    cur = float(last.get("tvl"))
    prv = float(prev.get("tvl"))
    chg = ((cur - prv) / prv * 100) if prv else 0.0
    return {
        "chain": "Solana",
        "tvl_usd": round(cur, 2),
        "tvl_chg_pct_approx": round(chg, 3),
        "date": last.get("date"),
    }


def fetch_btc_etf_flows_farside() -> dict[str, Any]:
    """Best-effort scrape of Farside BTC ETF flow table (free public page)."""
    url = "https://farside.co.uk/btc/"
    try:
        res = requests.get(url, headers=UA, timeout=25)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        tables = soup.find_all("table")
        if not tables:
            return {"source": url, "error": "table not found"}
        # Heuristic: take first sizable table text rows
        rows = []
        for tr in tables[0].find_all("tr")[:8]:
            cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if cols:
                rows.append(cols)
        return {"source": url, "preview_rows": rows[:6], "note": "BTC spot ETF flow preview (Farside)"}
    except Exception as exc:  # noqa: BLE001
        return {"source": url, "error": str(exc)}


def collect_onchain() -> dict[str, Any]:
    prices = fetch_prices()
    tvl: dict[str, Any] = {}
    for ticker, slug in DEFILLAMA_PROTOCOLS.items():
        try:
            if ticker == "SOL" or slug is None:
                tvl[ticker] = fetch_solana_chain_tvl()
            else:
                tvl[ticker] = fetch_defillama_protocol(slug)
        except Exception as exc:  # noqa: BLE001
            tvl[ticker] = {"error": str(exc)}

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "tvl": tvl,
        "etf": {
            "btc": fetch_btc_etf_flows_farside(),
            "eth_note": "ETH 현물 ETF 수급은 무료 공개 소스가 불안정해 뉴스 헤드라인으로 보완",
        },
    }
