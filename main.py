#!/usr/bin/env python3
"""크립토 & 매크로 모닝 브리핑 파이프라인

사용:
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env   # 키 입력
  python3 main.py
  python3 main.py --dry-run
  python3 main.py --no-telegram
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime, timezone

from briefing.config import get_settings
from briefing.collectors import (
    collect_guru_mentions,
    collect_macro,
    collect_news,
    collect_onchain,
)
from briefing.portfolio import build_portfolio, prepend_portfolio_section
from briefing.report import save_report
from briefing.summarizer import fallback_report, summarize_with_llm
from briefing.telegram import send_morning_brief


def gather_all(settings):
    print("[1/5] 뉴스 수집 (CryptoPanic + CoinDesk)…")
    news = collect_news(settings)
    print(f"  → unique headlines: {news.get('counts', {}).get('unique')}")

    print("[2/5] 매크로 수집 (Yahoo/FRED)…")
    macro = collect_macro(settings)
    print(f"  → yahoo keys: {list((macro.get('yahoo') or {}).keys())}")

    print("[3/5] 가격·TVL·ETF 수집…")
    onchain = collect_onchain()
    print(f"  → prices: {list((onchain.get('prices') or {}).keys())}")

    print("[4/5] 포트폴리오 평단/수익률 계산…")
    portfolio = build_portfolio(onchain.get("prices") or {})
    print(f"  → positions: {len(portfolio.get('positions') or [])}")

    print("[5/5] 구루 멘션 필터…")
    gurus = collect_guru_mentions(settings, news_bundle=news)
    print(f"  → mentor hits: {len(gurus.get('items') or [])}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "news": news,
        "macro": macro,
        "onchain": onchain,
        "portfolio": portfolio,
        "gurus": gurus,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crypto & Macro Morning Briefing")
    parser.add_argument("--dry-run", action="store_true", help="LLM 없이 초안만 저장")
    parser.add_argument("--dump-json", action="store_true", help="수집 JSON도 함께 저장")
    parser.add_argument("--no-telegram", action="store_true", help="텔레그램 발송 생략")
    parser.add_argument(
        "--send-latest",
        action="store_true",
        help="최신 reports/latest.md 만 텔레그램으로 재전송",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    dry_run = args.dry_run or settings.dry_run
    today = date.today()

    if args.send_latest:
        latest = settings.report_dir / "latest.md"
        if not latest.exists():
            print(f"latest.md 없음: {latest}", file=sys.stderr)
            return 1
        md = latest.read_text(encoding="utf-8")
        if not settings.telegram_enabled:
            print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 를 .env에 설정하세요.", file=sys.stderr)
            return 1
        print("Sending latest.md to Telegram…")
        send_morning_brief(settings, md)
        return 0

    try:
        payload = gather_all(settings)
    except Exception:
        traceback.print_exc()
        return 1

    if args.dump_json:
        settings.report_dir.mkdir(parents=True, exist_ok=True)
        raw_path = settings.report_dir / f"raw-{today.isoformat()}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON saved: {raw_path}")

    try:
        if dry_run:
            print("LLM skipped (dry-run). Building fallback markdown…")
            md = fallback_report(today, payload)
        else:
            print(f"Summarizing with LLM provider={settings.llm_provider}…")
            md = summarize_with_llm(settings, today, payload)
    except Exception as exc:
        print(f"LLM failed ({exc}). Falling back to raw draft…", file=sys.stderr)
        md = fallback_report(today, payload)

    # 포트폴리오 섹션은 계산값으로 맨 위 고정 삽입 (텔레그램/파일 공통)
    md = prepend_portfolio_section(md, payload.get("portfolio") or {})

    out = save_report(settings.report_dir, today, md)
    print(f"Report saved: {out}")
    print(f"Latest: {settings.report_dir / 'latest.md'}")

    if args.no_telegram:
        print("Telegram skipped (--no-telegram).")
    elif not settings.telegram_enabled:
        print("Telegram skipped (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정).")
    else:
        try:
            print("Sending report to Telegram…")
            send_morning_brief(settings, md)
            print("Telegram sent.")
        except Exception as exc:
            print(f"Telegram failed: {exc}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
