# 크립토 & 매크로 모닝 브리핑

매일 아침 관심 종목(BTC, ETH, SOL, CRCL, ONDO, LINK, TAO)과 매크로 지표를 모아
**Gemini**로 요약한 뒤 **텔레그램**으로 보내는 Python 파이프라인입니다.

## 빠른 시작

```bash
cd "/Users/kibong/크립토-뉴스"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### `.env` 필수 키

| 키 | 설명 |
|----|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) 발급 |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 아래 방법으로 확인한 chat id |
| `CRYPTOPANIC_API_KEY` | (권장) 뉴스 보강 |

### 평단가 / 거미줄 설정

`.env` 예시:

```env
BTC_AVG_PRICE=95000000
BTC_QTY=0.05
BTC_CCY=KRW
BTC_SPIDER_ORDERS=90000000:0.02,85000000:0.03

CRCL_AVG_PRICE=62.5
CRCL_QTY=100
CRCL_CCY=USD
CRCL_SPIDER_ORDERS=55:50,48:50

TAO_AVG_PRICE=320
TAO_QTY=5
TAO_CCY=USD
TAO_SPIDER_ORDERS=280:2,240:3

USDKRW_RATE=1350
```

또는 `cp config.example.json config.json` 후 수정.

계산 항목:
- 현재 수익률 (%)
- 평가 손익 (USD / KRW)
- 거미줄 전량 체결 시 예상 평단

리포트·텔레그램 맨 위에 `📊 내 포트폴리오 현황`이 붙고,
Gemini가 `🎯 대표님의 현재 평단가 대비 실전 대응 전략` 1줄을 제언합니다.

선택:

- `GEMINI_MODEL=gemini-2.5-flash` (기본) 또는 `gemini-2.5-pro`
- `FRED_API_KEY`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (`LLM_PROVIDER=openai|anthropic`)

### 텔레그램 chat id 찾는 법

1. BotFather로 봇 생성 → 토큰을 `TELEGRAM_BOT_TOKEN`에 넣기  
2. 봇에게 아무 메시지 보내기 (그룹이면 봇을 초대 후 메시지)  
3. 브라우저에서 열기:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

4. JSON의 `result[].message.chat.id` 값을 `TELEGRAM_CHAT_ID`에 넣기  
   (그룹은 보통 `-100...` 형태)

## 실행

```bash
# 수집 → Gemini 요약 → 파일 저장 → 텔레그램 발송
python3 main.py

# LLM/텔레그램 없이 수집 초안만
python3 main.py --dry-run --no-telegram --dump-json

# 텔레그램만 끄고 리포트 생성
python3 main.py --no-telegram

# 이미 만든 latest.md 재전송
python3 main.py --send-latest
```

결과물:

- `reports/morning-brief-YYYY-MM-DD.md`
- `reports/latest.md`

## 파이프라인 단계

1. 뉴스 (CryptoPanic + CoinDesk)
2. 매크로 (yfinance / FRED)
3. 가격·TVL·ETF
4. 구루 멘션 필터
5. **Gemini 2.5 Flash/Pro 분석 리포트**
6. **텔레그램 자동 발송**

## cron (매일 아침 07:00 KST)

```cron
0 7 * * * cd "/Users/kibong/크립토-뉴스" && /Users/kibong/크립토-뉴스/.venv/bin/python main.py >> "/Users/kibong/크립토-뉴스/reports/cron.log" 2>&1
```

## 웹 대시보드 (선택)

```bash
python3 server.py
# http://127.0.0.1:8787
```
