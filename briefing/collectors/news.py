from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from briefing.config import ALL_TICKERS, COINDESK_RSS, CRYPTOPANIC_CURRENCIES, Settings

UA = {"User-Agent": "SignalDeskMorningBrief/1.0"}

TICKER_PATTERNS = {
    "BTC": [r"\bbtc\b", r"bitcoin", r"비트코인"],
    "ETH": [r"\beth\b", r"ethereum", r"이더리움"],
    "SOL": [r"\bsol\b", r"solana", r"솔라나"],
    "XRP": [r"\bxrp\b", r"ripple", r"리플"],
    "CRCL": [r"\bcrcl\b", r"\bcircle\b", r"usdc", r"arc mainnet"],
    "ONDO": [r"\bondo\b", r"\brwa\b", r"ousg"],
    "LINK": [r"\blink\b", r"chainlink", r"ccip"],
    "TAO": [r"\btao\b", r"bittensor", r"subnet"],
}


def _match_tickers(text: str) -> list[str]:
    hay = text.lower()
    hits = []
    for ticker, patterns in TICKER_PATTERNS.items():
        if any(re.search(p, hay, re.I) for p in patterns):
            hits.append(ticker)
    return hits


def _normalize_item(
    *,
    title: str,
    url: str,
    source: str,
    published: str = "",
    currencies: list[str] | None = None,
) -> dict[str, Any] | None:
    title = (title or "").strip()
    url = (url or "").strip()
    if not title:
        return None
    tickers = currencies or _match_tickers(f"{title} {url}")
    if not tickers:
        # keep macro-ish / circle-adjacent anyway if keywords present
        if not _match_tickers(title):
            return None
    return {
        "title": title,
        "url": url,
        "source": source,
        "published": published,
        "tickers": tickers or _match_tickers(title),
    }


def fetch_cryptopanic(settings: Settings, limit: int = 40) -> list[dict[str, Any]]:
    if not settings.cryptopanic_api_key:
        print("  ! CRYPTOPANIC_API_KEY 없음 — CoinDesk RSS만 사용")
        return []

    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": settings.cryptopanic_api_key,
        "currencies": CRYPTOPANIC_CURRENCIES,
        "public": "true",
        "kind": "news",
    }
    try:
        res = requests.get(url, params=params, headers=UA, timeout=20)
        if res.status_code >= 400:
            # try developer v2 path
            url = "https://cryptopanic.com/api/developer/v2/posts/"
            res = requests.get(url, params=params, headers=UA, timeout=20)
        res.raise_for_status()
        payload = res.json()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! CryptoPanic error: {exc}")
        return []

    items: list[dict[str, Any]] = []
    for row in payload.get("results", [])[:limit]:
        currencies = [
            c.get("code")
            for c in (row.get("currencies") or [])
            if isinstance(c, dict) and c.get("code") in ALL_TICKERS
        ]
        title = row.get("title") or ""
        if not currencies:
            currencies = _match_tickers(title)
        item = _normalize_item(
            title=title,
            url=(row.get("url") or row.get("original_url") or ""),
            source="CryptoPanic",
            published=str(row.get("published_at") or row.get("created_at") or ""),
            currencies=currencies,
        )
        if item:
            items.append(item)
    return items


MACRO_NEWS_RE = re.compile(
    r"fed|fomc|treasury|inflation|cpi|pce|dollar|dxy|etf|sec|macro|rate cut|rate hike",
    re.I,
)


def fetch_coindesk_rss(limit: int = 40) -> list[dict[str, Any]]:
    try:
        res = requests.get(COINDESK_RSS, headers=UA, timeout=20)
        res.raise_for_status()
        feed = feedparser.parse(res.content)
    except Exception as exc:  # noqa: BLE001
        return [{"title": f"[오류] CoinDesk RSS: {exc}", "url": "", "source": "system", "published": "", "tickers": []}]

    items: list[dict[str, Any]] = []
    for entry in feed.entries[:80]:
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        published = ""
        if getattr(entry, "published_parsed", None):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        tickers = _match_tickers(title)
        # 관심 종목 매칭 또는 매크로/ETF 이슈는 포함
        if not tickers and not MACRO_NEWS_RE.search(title):
            continue
        items.append(
            {
                "title": title.strip(),
                "url": link,
                "source": "CoinDesk",
                "published": published,
                "tickers": tickers,
            }
        )
        if len(items) >= limit:
            break
    return items


def collect_news(settings: Settings) -> dict[str, Any]:
    panic = fetch_cryptopanic(settings)
    desk = fetch_coindesk_rss()
    merged = panic + desk

    by_ticker: dict[str, list[dict[str, Any]]] = {t: [] for t in ALL_TICKERS}
    for item in merged:
        for t in item.get("tickers") or []:
            if t in by_ticker and len(by_ticker[t]) < 8:
                by_ticker[t].append(item)

    # de-dupe titles
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in merged:
        key = item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "items": unique[:60],
        "by_ticker": by_ticker,
        "counts": {
            "cryptopanic": len(panic),
            "coindesk": len(desk),
            "unique": len(unique),
        },
    }
