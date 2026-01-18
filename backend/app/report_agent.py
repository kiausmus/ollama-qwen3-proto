from datetime import date, timedelta

from fastapi import HTTPException

from .config import OLLAMA_MODEL
from .schemas import StockReportRequest, StockReportResponse


async def run_stock_report(req: StockReportRequest, finn, client, chat_context: str) -> StockReportResponse:
    symbol = req.symbol.strip().upper()
    audience = (req.audience or "장기 투자자").strip()
    focus = (req.focus or "펀더멘털 중심").strip()

    try:
        quote = await finn.quote(symbol)
        profile = await finn.profile2(symbol)
        metrics = await finn.metrics(symbol)

        today = date.today()
        frm = (today - timedelta(days=30)).isoformat()
        news = await finn.news(symbol, frm, today.isoformat())
        if isinstance(news, list):
            news = news[:8]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Finnhub 호출 실패: {e}")

    prompt = f"""
너는 금융 리서치 애널리스트다.
대상 종목: {symbol}
대상 독자: {audience}
분석 초점: {focus}

아래 데이터와 "대화 내역"만 근거로 보고서를 작성하라. 모르면 모른다고 말해라.
과장 금지. 추정은 '추정'으로 표시.
투자 조언이 아니라 정보 제공이며, 마지막에 리스크 고지 1줄.

[대화 내역]
{chat_context}

[quote]
{quote}

[profile2]
{profile}

[metrics]
{metrics}

[news(최근30일, 최대8개)]
{news}

[출력 템플릿 - Markdown]
## 개요
- 요약: 3~5줄
- 사용자가 중시한 키워드: 3~5개

## 기업/사업 스냅샷
- 핵심 제품/서비스
- 지역/섹터
- 최근 뉴스 요약(1~3줄)

## 펀더멘털 체크포인트 (5)
1) ...
2) ...
3) ...
4) ...
5) ...

## 밸류에이션 스냅샷
- 주요 지표 코멘트(추정은 '추정' 표기)
- 비교 관점(동종 업계/지수 기준)

## 모멘텀/수급 단서
- quote/뉴스 기반 3가지

## 리스크 (5)
1) ...
2) ...
3) ...
4) ...
5) ...

## 향후 촉매/관찰 포인트 (5)
1) ...
2) ...
3) ...
4) ...
5) ...

## 결론
- 장기/적립식 관점 2~3줄
- 한 문장 리스크 고지
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "한국어로, 근거 중심으로 답하라."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": "1h",
    }

    try:
        data = await client.chat(payload)
        content = (data.get("message") or {}).get("content", "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 호출 실패: {e}")

    return StockReportResponse(symbol=symbol, report=content)
