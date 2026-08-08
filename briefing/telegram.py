from __future__ import annotations

import re

import requests

from briefing.config import Settings

TELEGRAM_API = "https://api.telegram.org"
MAX_LEN = 3900  # Telegram 4096 제한보다 여유


def _chunk_text(text: str, limit: int = MAX_LEN) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    parts = re.split(r"(\n\n+)", text)
    buf = ""
    for part in parts:
        if len(buf) + len(part) <= limit:
            buf += part
            continue
        if buf.strip():
            chunks.append(buf.strip())
        if len(part) <= limit:
            buf = part
        else:
            for i in range(0, len(part), limit):
                piece = part[i : i + limit].strip()
                if piece:
                    chunks.append(piece)
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def send_telegram_message(settings: Settings, text: str) -> list[dict]:
    """텔레그램 채팅방으로 메시지 전송. 길면 분할 발송."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 필요합니다.")

    url = f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendMessage"
    results = []
    for i, chunk in enumerate(_chunk_text(text), start=1):
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        res = requests.post(url, json=payload, timeout=30)
        if not res.ok:
            raise RuntimeError(f"Telegram send failed ({res.status_code}): {res.text[:300]}")
        data = res.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        results.append(data)
        print(f"  → telegram chunk {i} sent")
    return results


def send_morning_brief(settings: Settings, markdown: str) -> list[dict]:
    """모닝 브리핑 Markdown을 텔레그램으로 발송.
    맨 위 포트폴리오 섹션이 보이도록 헤더를 붙인다.
    """
    body = markdown.strip()
    if not body.startswith("📡"):
        body = "📡 오늘 아침 핵심 피드\n\n" + body
    # 텔레그램에서도 포트폴리오가 상단에 오도록 보장
    if "📊 내 포트폴리오 현황" in body and not re.search(
        r"📡[\s\S]{0,80}📊 내 포트폴리오 현황", body
    ):
        # 제목/헤더 다음으로 이미 prepend_portfolio_section 처리된 본문을 그대로 사용
        pass
    return send_telegram_message(settings, body)
