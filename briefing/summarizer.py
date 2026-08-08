from __future__ import annotations

import json
from datetime import date
from typing import Any

from briefing.config import Settings


SYSTEM_PROMPT = """너는 가상자산 및 매크로 전문 리서처다.
입력된 원시 데이터만 근거로 "오늘 아침 핵심 피드"를 작성한다.

원칙:
1) 없는 수치·뉴스를 만들지 않는다. 없으면 '확인 필요'.
2) 투자자 관점에서 3분 안에 읽을 수 있게 짧고 명확하게 쓴다.
3) 단기 변동성 요인, BTC/ETH 수급, CRCL/RWA 주요 뉴스, 매크로(금리/DXY) 핵심을 반드시 다룬다.
4) 연준은 현행 FOMC·금리 경로 중심으로 쓰고, 특정 전임 의장에 고정하지 않는다.
5) 관심 종목: BTC, ETH, SOL, XRP, CRCL, ONDO, LINK, TAO.
6) Arthur Hayes / Raoul Pal / Jeremy Allaire 언급이 있을 때만 짧게 반영.
7) portfolio 데이터가 있으면 반드시 마지막에
   '🎯 대표님의 현재 평단가 대비 실전 대응 전략: ...' 한 줄 맞춤 제언을 추가한다.
8) 지정된 Markdown 섹션 헤더 형식을 그대로 따른다.
   (포트폴리오 숫자 표는 시스템이 별도 삽입하므로 중복 작성하지 말 것)
"""


def build_user_prompt(today: date, payload: dict[str, Any]) -> str:
    return f"""오늘 날짜: {today.isoformat()}

입력된 원시 데이터를 바탕으로 "오늘 아침 핵심 피드"를 작성해라.
단기 변동성 요인, BTC/ETH 수급, CRCL/RWA 주요 뉴스, 매크로(금리/DXY) 핵심을
투자자 관점에서 3분 안에 읽을 수 있도록 요약해라.

portfolio 필드에는 대표님의 평단가·수량·수익률·거미줄(하방 지정가) 체결 시 예상 평단이 있다.
이를 반영해 마지막에 딱 1줄로
"🎯 대표님의 현재 평단가 대비 실전 대응 전략: ..."
형식의 맞춤 제언을 작성해라. (포트폴리오 표는 쓰지 말 것)

출력 양식(Markdown만):

# 📅 [{today.isoformat()}] 크립토 & 매크로 모닝 브리핑

## 1. 🌐 거시경제 & 매크로 지표
- DXY / US10Y / 연준 금리 관련 주요 뉴스 summary

## 2. 🪙 핵심 종목별 주요 이슈 (BTC, ETH, SOL)
- 가격 변화 및 현물 ETF 유출입/주요 헤드라인

## 3. 🏦 RWA & 기관 서클 생태계 (CRCL, ONDO, LINK)
- CRCL 실적/서클 및 Arc 메인넷 관련 이슈
- RWA TVL 및 온체인 호재 요약

## 4. 🤖 AI & DePIN (TAO)
- TAO 관련 서브넷 및 AI 칩/매크로 연동 이슈

## 5. 💡 오늘 하루 체크할 핵심 포인트 (3줄 요약)

🎯 대표님의 현재 평단가 대비 실전 대응 전략: (1줄)

수집 데이터(JSON):
```json
{json.dumps(payload, ensure_ascii=False, indent=2)[:120000]}
```
"""


def summarize_with_gemini(settings: Settings, today: date, payload: dict[str, Any]) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY 가 필요합니다.")

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(today, payload)}"
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not text:
        # SDK 버전에 따라 candidates 구조가 다를 수 있음
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Gemini 응답 파싱 실패: {exc}") from exc
    return str(text).strip()


def summarize_with_llm(settings: Settings, today: date, payload: dict[str, Any]) -> str:
    user_prompt = build_user_prompt(today, payload)
    provider = settings.llm_provider

    if provider == "gemini":
        return summarize_with_gemini(settings, today, payload)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 가 필요합니다.")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY 가 필요합니다.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    # auto: gemini → openai → anthropic
    if settings.gemini_api_key:
        return summarize_with_gemini(settings, today, payload)
    if settings.openai_api_key:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    if settings.anthropic_api_key:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    raise RuntimeError("GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY 중 하나가 필요합니다.")


ARTICLE_SYSTEM_PROMPT = """너는 가상자산·매크로 리서치 데스크 애널리스트다.
뉴스 1건만 요약한다. 제공된 필드만 근거로 쓰고, 없는 사실·수치·인용은 만들지 않는다.
정보가 부족하면 짧게 '확인 필요'라고 한다.
한국어로, 짧고 실행 가능하게 정리한다.
"""


def build_article_prompt(article: dict[str, Any]) -> str:
    return f"""CRYPTO DESK용으로 아래 헤드라인을 한국어로 요약해라.

Markdown만 출력하고, 아래 형식을 그대로 따른다:

## 한줄 요약
(1-2문장)

## 핵심 포인트
- 짧은 불릿 3개

## 왜 중요한가
(시장/매크로/크립토 영향 2-4문장)

## 다음에 볼 것
- 짧은 불릿 2개

기사 JSON:
```json
{json.dumps(article, ensure_ascii=False, indent=2)[:12000]}
```
"""


def summarize_article_with_gemini(settings: Settings, article: dict[str, Any]) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required.")

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"{ARTICLE_SYSTEM_PROMPT}\n\n{build_article_prompt(article)}"
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not text:
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Gemini response parse failed: {exc}") from exc
    return str(text).strip()


def fallback_article_summary(article: dict[str, Any]) -> str:
    title = (article.get("title") or "제목 없음").strip()
    source = (article.get("source") or "출처 미상").strip()
    summary = (article.get("summary") or "").strip()
    link = (article.get("link") or "").strip()
    lines = [
        "## 한줄 요약",
        title,
        "",
        "## 핵심 포인트",
        f"- 출처: {source}",
    ]
    if summary:
        lines.append(f"- 피드 발췌: {summary[:420]}")
    else:
        lines.append("- 피드 요약문이 없습니다.")
    if link:
        lines.append(f"- 원문: {link}")
    lines += [
        "",
        "## 왜 중요한가",
        "로컬 추출본입니다. 전체 Gemini 요약을 쓰려면 `.env`에 `GEMINI_API_KEY`를 설정하세요.",
        "",
        "## 다음에 볼 것",
        "- 원문에서 세부 맥락 확인",
        "- 워치리스트 관련 종목과 교차 점검",
    ]
    return "\n".join(lines)


def summarize_article(settings: Settings, article: dict[str, Any]) -> tuple[str, str]:
    """Returns (markdown, mode) where mode is gemini|fallback."""
    try:
        if settings.gemini_api_key:
            return summarize_article_with_gemini(settings, article), "gemini"
    except Exception:
        pass
    return fallback_article_summary(article), "fallback"


def fallback_report(today: date, payload: dict[str, Any]) -> str:
    """DRY_RUN / LLM 실패 시 원천 데이터 초안."""
    macro = payload.get("macro", {}).get("yahoo", {})
    prices = payload.get("onchain", {}).get("prices", {})
    lines = [
        f"# 📅 [{today.isoformat()}] 크립토 & 매크로 모닝 브리핑",
        "",
        "> DRY_RUN/폴백 초안 — LLM 요약 전 원천 데이터 요약",
        "",
        "## 1. 🌐 거시경제 & 매크로 지표",
    ]
    for k in ("DXY", "US10Y", "SPX"):
        row = macro.get(k, {})
        if "last" in row:
            lines.append(f"- {k}: {row['last']} ({row.get('chg_pct')}%)")
        else:
            lines.append(f"- {k}: {row}")
    lines += ["", "## 2. 🪙 핵심 종목별 주요 이슈 (BTC, ETH, SOL)"]
    for t in ("BTC", "ETH", "SOL"):
        p = prices.get(t, {})
        lines.append(f"- {t}: {p}")
        for n in (payload.get("news", {}).get("by_ticker", {}).get(t) or [])[:3]:
            lines.append(f"  - {n.get('title')}")
    lines += ["", "## 3. 🏦 RWA & 기관 서클 생태계 (CRCL, ONDO, LINK)"]
    for t in ("CRCL", "ONDO", "LINK"):
        lines.append(f"- {t} price: {prices.get(t)}")
        lines.append(f"- {t} tvl: {payload.get('onchain', {}).get('tvl', {}).get(t)}")
        for n in (payload.get("news", {}).get("by_ticker", {}).get(t) or [])[:3]:
            lines.append(f"  - {n.get('title')}")
    lines += ["", "## 4. 🤖 AI & DePIN (TAO)"]
    lines.append(f"- TAO: {prices.get('TAO')}")
    for n in (payload.get("news", {}).get("by_ticker", {}).get("TAO") or [])[:5]:
        lines.append(f"  - {n.get('title')}")
    lines += ["", "## 5. 💡 오늘 하루 체크할 핵심 포인트 (3줄 요약)"]
    gurus = payload.get("gurus", {}).get("items") or []
    if gurus:
        lines.append(f"- 구루 멘션 {len(gurus)}건 확인")
    lines.append("- 매크로(DXY/US10Y)와 BTC ETF 수급 동시 점검")
    lines.append("- CRCL/ONDO/LINK RWA 플로우와 TAO 서브넷 헤드라인 재확인")
    if payload.get("portfolio", {}).get("positions"):
        lines.append("")
        lines.append(
            "🎯 대표님의 현재 평단가 대비 실전 대응 전략: "
            "평단 대비 손실 구간은 거미줄 체결 후 평단 하향을 확인하고, "
            "수익 구간은 분할 익절·비중 조절을 검토 (LLM dry-run 플레이스홀더)."
        )
    return "\n".join(lines) + "\n"
