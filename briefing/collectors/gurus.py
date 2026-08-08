from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from briefing.config import GURUS, Settings
from briefing.collectors.news import fetch_coindesk_rss, fetch_cryptopanic

UA = {"User-Agent": "SignalDeskMorningBrief/1.0"}

EXTRA_FEEDS = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
]


def _guru_hits(text: str) -> list[str]:
    hits = []
    for name in GURUS:
        # allow partial last-name matches carefully
        parts = name.split()
        patterns = [re.escape(name)]
        if len(parts) >= 2:
            patterns.append(rf"\b{re.escape(parts[-1])}\b")
        if any(re.search(p, text, re.I) for p in patterns):
            # avoid generic "Pal" false positives somewhat
            if parts[-1].lower() == "pal" and "raoul" not in text.lower() and "real vision" not in text.lower():
                if not re.search(r"raoul\s+pal", text, re.I):
                    continue
            hits.append(name)
    return sorted(set(hits))


def _from_rss(limit_per_feed: int = 25) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source, url in EXTRA_FEEDS:
        try:
            res = requests.get(url, headers=UA, timeout=20)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:limit_per_feed]:
                title = getattr(entry, "title", "") or ""
                link = getattr(entry, "link", "") or ""
                summary = getattr(entry, "summary", "") or ""
                text = f"{title} {summary}"
                gurus = _guru_hits(text)
                if not gurus:
                    continue
                items.append(
                    {
                        "title": title.strip(),
                        "url": link,
                        "source": source,
                        "gurus": gurus,
                        "snippet": re.sub(r"<[^>]+>", "", summary)[:280],
                    }
                )
        except Exception as exc:  # noqa: BLE001
            items.append(
                {
                    "title": f"[오류] {source}: {exc}",
                    "url": "",
                    "source": "system",
                    "gurus": [],
                    "snippet": "",
                }
            )
    return items


def collect_guru_mentions(settings: Settings, news_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    X(Twitter) API는 유료 키가 필요해 기본은 뉴스/RSS 헤드라인에서
    Arthur Hayes / Raoul Pal / Jeremy Allaire 멘션을 필터링한다.
    """
    pool: list[dict[str, Any]] = []

    if news_bundle:
        for item in news_bundle.get("items", []):
            text = item.get("title", "")
            gurus = _guru_hits(text)
            if gurus:
                pool.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source": item.get("source"),
                        "gurus": gurus,
                        "snippet": "",
                    }
                )
    else:
        for item in fetch_cryptopanic(settings) + fetch_coindesk_rss():
            gurus = _guru_hits(item.get("title", ""))
            if gurus:
                pool.append({**item, "gurus": gurus, "snippet": ""})

    pool.extend(_from_rss())

    # de-dupe
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in pool:
        key = (item.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    by_guru = {g: [] for g in GURUS}
    for item in unique:
        for g in item.get("gurus") or []:
            if g in by_guru and len(by_guru[g]) < 8:
                by_guru[g].append(item)

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "method": "news_rss_filter",
        "note": "X API 미사용. 헤드라인/RSS에서 구루 이름 필터링.",
        "items": unique[:40],
        "by_guru": by_guru,
    }
