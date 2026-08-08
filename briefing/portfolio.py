from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yfinance as yf

from briefing.config import ALL_TICKERS, ROOT

UA = {"User-Agent": "SignalDeskMorningBrief/1.0"}


@dataclass
class SpiderOrder:
    price: float
    qty: float


@dataclass
class Holding:
    ticker: str
    avg_price: float
    qty: float
    currency: str = "USD"  # USD | KRW
    spider_orders: list[SpiderOrder] = field(default_factory=list)


def _f(val: str | None) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return None


def _parse_spider(raw: str) -> list[SpiderOrder]:
    """Format: price:qty,price:qty  e.g. 90000000:0.02,85000000:0.03"""
    orders: list[SpiderOrder] = []
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        p, q = part.split(":", 1)
        price, qty = _f(p), _f(q)
        if price is None or qty is None or qty <= 0:
            continue
        orders.append(SpiderOrder(price=price, qty=qty))
    return orders


def load_holdings_from_env() -> dict[str, Holding]:
    holdings: dict[str, Holding] = {}
    for ticker in ALL_TICKERS:
        avg = _f(os.getenv(f"{ticker}_AVG_PRICE"))
        if avg is None:
            continue
        qty = _f(os.getenv(f"{ticker}_QTY")) or 0.0
        ccy = (os.getenv(f"{ticker}_CCY") or os.getenv(f"{ticker}_CURRENCY") or "USD").strip().upper()
        if ccy not in {"USD", "KRW"}:
            ccy = "USD"
        spiders = _parse_spider(os.getenv(f"{ticker}_SPIDER_ORDERS", "") or "")
        holdings[ticker] = Holding(
            ticker=ticker,
            avg_price=avg,
            qty=qty,
            currency=ccy,
            spider_orders=spiders,
        )
    return holdings


def load_holdings_from_json(path: Path) -> tuple[dict[str, Holding], float | None]:
    if not path.exists():
        return {}, None
    data = json.loads(path.read_text(encoding="utf-8"))
    usdkrw = _f(str(data.get("usdkrw"))) if data.get("usdkrw") is not None else None
    holdings: dict[str, Holding] = {}
    for ticker, row in (data.get("holdings") or {}).items():
        ticker = str(ticker).upper()
        avg = _f(str(row.get("avg_price")))
        if avg is None:
            continue
        qty = _f(str(row.get("qty"))) or 0.0
        ccy = str(row.get("currency") or "USD").upper()
        spiders = []
        for od in row.get("spider_orders") or []:
            price = _f(str(od.get("price")))
            q = _f(str(od.get("qty")))
            if price is None or q is None or q <= 0:
                continue
            spiders.append(SpiderOrder(price=price, qty=q))
        holdings[ticker] = Holding(
            ticker=ticker,
            avg_price=avg,
            qty=qty,
            currency=ccy if ccy in {"USD", "KRW"} else "USD",
            spider_orders=spiders,
        )
    return holdings, usdkrw


def fetch_usdkrw() -> float | None:
    env = _f(os.getenv("USDKRW_RATE"))
    if env:
        return env
    try:
        hist = yf.Ticker("USDKRW=X").history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    try:
        res = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=KRW",
            headers=UA,
            timeout=15,
        )
        if res.ok:
            return float(res.json()["rates"]["KRW"])
    except Exception:
        pass
    return None


def _extract_price(price_row: dict[str, Any] | None) -> float | None:
    if not price_row or price_row.get("error"):
        return None
    last = price_row.get("last")
    try:
        return float(last)
    except (TypeError, ValueError):
        return None


def projected_avg_after_spiders(holding: Holding) -> dict[str, Any] | None:
    if not holding.spider_orders:
        return None
    cost = holding.avg_price * holding.qty
    qty = holding.qty
    filled = []
    for od in sorted(holding.spider_orders, key=lambda x: x.price, reverse=True):
        cost += od.price * od.qty
        qty += od.qty
        filled.append({"price": od.price, "qty": od.qty})
    if qty <= 0:
        return None
    return {
        "new_avg_price": round(cost / qty, 6),
        "new_qty": round(qty, 8),
        "orders": filled,
        "note": "하방 지정가(거미줄) 전량 체결 가정",
    }


def build_portfolio(prices: dict[str, Any]) -> dict[str, Any]:
    json_path = ROOT / "config.json"
    from_json, json_fx = load_holdings_from_json(json_path)
    from_env = load_holdings_from_env()
    # env overrides json per ticker
    holdings = {**from_json, **from_env}

    usdkrw = json_fx or fetch_usdkrw()
    positions = []
    total_pnl_usd = 0.0
    total_cost_usd = 0.0
    total_value_usd = 0.0

    for ticker in ALL_TICKERS:
        h = holdings.get(ticker)
        if not h:
            continue
        current_usd = _extract_price(prices.get(ticker))
        if current_usd is None:
            positions.append(
                {
                    "ticker": ticker,
                    "error": "현재가 없음",
                    "avg_price": h.avg_price,
                    "qty": h.qty,
                    "currency": h.currency,
                }
            )
            continue

        # normalize everything to holding currency + USD
        if h.currency == "KRW":
            if not usdkrw:
                positions.append(
                    {
                        "ticker": ticker,
                        "error": "USDKRW 환율 없음 (USDKRW_RATE 또는 config.json usdkrw 설정)",
                        "avg_price": h.avg_price,
                        "qty": h.qty,
                        "currency": h.currency,
                        "current_price_usd": current_usd,
                    }
                )
                continue
            current = current_usd * usdkrw
            avg = h.avg_price
            pnl_native = (current - avg) * h.qty
            pnl_usd = pnl_native / usdkrw
            cost_usd = (avg * h.qty) / usdkrw
            value_usd = (current * h.qty) / usdkrw
        else:
            current = current_usd
            avg = h.avg_price
            pnl_native = (current - avg) * h.qty
            pnl_usd = pnl_native
            cost_usd = avg * h.qty
            value_usd = current * h.qty

        pnl_pct = ((current - avg) / avg * 100) if avg else 0.0
        spider = projected_avg_after_spiders(h)

        # spider projected avg vs current (same currency as holding)
        spider_vs_now = None
        if spider:
            spider_vs_now = round(((current - spider["new_avg_price"]) / spider["new_avg_price"]) * 100, 3)

        row = {
            "ticker": ticker,
            "qty": h.qty,
            "currency": h.currency,
            "avg_price": h.avg_price,
            "current_price": round(current, 6),
            "current_price_usd": round(current_usd, 6),
            "pnl_pct": round(pnl_pct, 3),
            "pnl_native": round(pnl_native, 2),
            "pnl_usd": round(pnl_usd, 2),
            "pnl_krw": round(pnl_usd * usdkrw, 0) if usdkrw else None,
            "cost_usd": round(cost_usd, 2),
            "value_usd": round(value_usd, 2),
            "spider_projected": spider,
            "spider_pnl_pct_if_filled_vs_now": spider_vs_now,
        }
        positions.append(row)
        total_pnl_usd += pnl_usd
        total_cost_usd += cost_usd
        total_value_usd += value_usd

    total_pnl_pct = (total_pnl_usd / total_cost_usd * 100) if total_cost_usd else None

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "usdkrw": round(usdkrw, 2) if usdkrw else None,
        "positions": positions,
        "totals": {
            "cost_usd": round(total_cost_usd, 2),
            "value_usd": round(total_value_usd, 2),
            "pnl_usd": round(total_pnl_usd, 2),
            "pnl_krw": round(total_pnl_usd * usdkrw, 0) if usdkrw else None,
            "pnl_pct": round(total_pnl_pct, 3) if total_pnl_pct is not None else None,
        },
    }


def format_portfolio_section(portfolio: dict[str, Any]) -> str:
    lines = ["## 📊 내 포트폴리오 현황", ""]
    positions = portfolio.get("positions") or []
    if not positions:
        lines.append("- 평단가 미설정 (`.env`의 `BTC_AVG_PRICE` 또는 `config.json` 참고)")
        lines.append("")
        return "\n".join(lines)

    fx = portfolio.get("usdkrw")
    if fx:
        lines.append(f"- 기준 환율 USDKRW: {fx}")
        lines.append("")

    for p in positions:
        if p.get("error"):
            lines.append(f"- **{p['ticker']}**: {p['error']}")
            continue
        sign = "+" if p["pnl_pct"] >= 0 else ""
        ccy = p["currency"]
        avg = p["avg_price"]
        cur = p["current_price"]
        if ccy == "KRW":
            avg_s = f"₩{avg:,.0f}"
            cur_s = f"₩{cur:,.0f}"
            pnl_s = f"₩{p['pnl_native']:,.0f}"
        else:
            avg_s = f"${avg:,.4g}"
            cur_s = f"${cur:,.4g}"
            pnl_s = f"${p['pnl_native']:,.2f}"
        extra = f" / ${p['pnl_usd']:,.2f}"
        if p.get("pnl_krw") is not None and ccy != "KRW":
            extra += f" (≈₩{p['pnl_krw']:,.0f})"
        lines.append(
            f"- **{p['ticker']}** qty {p['qty']} | 평단 {avg_s} → 현재 {cur_s} | "
            f"수익률 {sign}{p['pnl_pct']:.2f}% | 평가손익 {sign}{pnl_s}{extra if ccy=='USD' else ''}"
        )
        sp = p.get("spider_projected")
        if sp:
            new_avg = sp["new_avg_price"]
            new_avg_s = f"₩{new_avg:,.0f}" if ccy == "KRW" else f"${new_avg:,.4g}"
            lines.append(
                f"  · 거미줄 전량 체결 시 예상 평단 {new_avg_s} "
                f"(신규 수량 {sp['new_qty']})"
            )

    totals = portfolio.get("totals") or {}
    if totals.get("pnl_pct") is not None:
        sign = "+" if totals["pnl_pct"] >= 0 else ""
        lines.append("")
        lines.append(
            f"- **합계** 평가손익 ${totals['pnl_usd']:,.2f}"
            + (f" (≈₩{totals['pnl_krw']:,.0f})" if totals.get("pnl_krw") is not None else "")
            + f" | 포트 수익률 {sign}{totals['pnl_pct']:.2f}%"
        )
    lines.append("")
    return "\n".join(lines)


def prepend_portfolio_section(markdown: str, portfolio: dict[str, Any]) -> str:
    section = format_portfolio_section(portfolio).rstrip() + "\n\n"
    body = markdown.lstrip()
    # 이미 섹션이 있으면 교체
    if re.search(r"^##\s*📊\s*내 포트폴리오 현황", body, flags=re.M):
        body = re.sub(
            r"^##\s*📊\s*내 포트폴리오 현황.*?(?=^#|\Z)",
            section,
            body,
            count=1,
            flags=re.M | re.S,
        )
        return body
    # 제목 바로 아래 삽입
    lines = body.splitlines()
    if lines and lines[0].startswith("#"):
        return lines[0] + "\n\n" + section + "\n".join(lines[1:]).lstrip("\n")
    return section + body
