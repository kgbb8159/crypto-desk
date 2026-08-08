from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

WATCH = {
    "top_tier": ["BTC", "ETH", "SOL", "XRP"],
    "rwa_circle": ["CRCL", "ONDO", "LINK"],
    "ai_depin": ["TAO"],
}

ALL_TICKERS = WATCH["top_tier"] + WATCH["rwa_circle"] + WATCH["ai_depin"]

GURUS = [
    "Arthur Hayes",
    "Raoul Pal",
    "Jeremy Allaire",
]

CRYPTOPANIC_CURRENCIES = "BTC,ETH,SOL,XRP,LINK,ONDO,TAO"

DEFILLAMA_PROTOCOLS = {
    "ONDO": "ondo-finance",
    "LINK": "chainlink",
    "SOL": None,  # Solana chain TVL
}

COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str
    openai_model: str
    anthropic_api_key: str
    anthropic_model: str
    gemini_api_key: str
    gemini_model: str
    cryptopanic_api_key: str
    fred_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_enabled: bool
    dry_run: bool
    report_dir: Path


def get_settings() -> Settings:
    report_dir = Path(os.getenv("REPORT_DIR", "reports"))
    if not report_dir.is_absolute():
        report_dir = ROOT / report_dir

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    telegram_flag = os.getenv("TELEGRAM_ENABLED", "true").strip().lower() in {"1", "true", "yes"}

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY", "").strip(),
        fred_api_key=os.getenv("FRED_API_KEY", "").strip(),
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat,
        telegram_enabled=telegram_flag and bool(telegram_token and telegram_chat),
        dry_run=os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes"},
        report_dir=report_dir,
    )
