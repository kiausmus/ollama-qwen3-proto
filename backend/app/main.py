import re
import json
import asyncio
from pathlib import Path
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker

from .schemas import (
    ChatRequest,
    ChatResponse,
    ShouldIBuyRequest,
    ShouldIBuyResponse,
    StockReportRequest,
    StockReportResponse,
)
from .ollama_client import OllamaClient
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL
from .finnhub_client import FinnhubClient
from .report_agent import run_stock_report

app = FastAPI(title="Ollama Qwen3 Prototype")
client = OllamaClient()
finn = FinnhubClient()

# --- 프론트 정적 파일 경로 (프로젝트 루트/frontend) ---
PROJECT_ROOT = (Path(__file__).resolve().parents[2]).resolve()
FRONTEND_DIR = (PROJECT_ROOT / "frontend").resolve()
DB_PATH = (PROJECT_ROOT / "backend" / "app" / "chat_logs.sqlite3").resolve()
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def summarize_messages(messages):
    if not messages:
        return "대화"
    user_parts = []
    for m in messages:
        if m.get("role") == "user":
            text = (m.get("content") or "").strip()
            if text:
                user_parts.append(text)
        if len(user_parts) >= 3:
            break
    if not user_parts:
        return "대화"
    merged = " / ".join(user_parts)
    merged = " ".join(merged.split())
    return merged[:80]


def get_or_create_session(db, session_id: str, name: str):
    session_row = db.query(Session).filter(Session.id == session_id).first()
    if session_row:
        return session_row
    session_row = Session(id=session_id, name=name or "대화")
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return session_row


def save_chat_log(message, session_id, session_name):
    db = SessionLocal()
    try:
        session_row = get_or_create_session(db, session_id, session_name)
        row = ChatLog(session_id=session_row.id, message=message)
        db.add(row)
        db.commit()
    finally:
        db.close()


def load_latest_session_context(session_id: str) -> str:
    db = SessionLocal()
    try:
        row = (
            db.query(ChatLog)
            .filter(ChatLog.session_id == session_id)
            .order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="session_id에 해당하는 채팅 내역이 없습니다.")
        try:
            payload = json.loads(row.message)
        except Exception:
            payload = {}
        messages = payload.get("messages") or []
        response = payload.get("response")
        lines = []
        for m in messages:
            role = (m.get("role") or "").strip()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            lines.append(f"{role}: {content}")
        if response:
            lines.append(f"assistant: {response}")
        context = "\n".join(lines).strip()
        return context or "대화 없음"
    finally:
        db.close()


if not FRONTEND_DIR.exists():
    print(f"[WARN] frontend directory not found: {FRONTEND_DIR}")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(str(index_path))


@app.get("/health")
async def health():
    return {"ok": True, "model": OLLAMA_MODEL, "ollama": OLLAMA_BASE_URL}


# -------------------------
# 티커 추출
# -------------------------
TICKER_RE = re.compile(r'(?<![A-Z0-9])\$?([A-Z]{1,6}(?:\.[A-Z]{1,2})?)(?![A-Z0-9])')


def extract_tickers(text: str, max_n: int = 1) -> list[str]:
    if not text:
        return []
    hits = [m.group(1) for m in TICKER_RE.finditer(text.upper())]
    blacklist = {"I", "A", "AN", "THE", "AND", "OR"}
    out = []
    for h in hits:
        if h in blacklist:
            continue
        if h not in out:
            out.append(h)
        if len(out) >= max_n:
            break
    return out


# -------------------------
# 채팅: 티커 감지 시 Finnhub 자동 주입
# -------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # messages normalize (dict/pydantic 둘 다)
    messages_in = []
    for m in req.messages:
        if isinstance(m, dict):
            messages_in.append({"role": m.get("role"), "content": m.get("content", "")})
        else:
            messages_in.append({"role": getattr(m, "role", None), "content": getattr(m, "content", "")})

    # 마지막 user 메시지
    last_user = ""
    for m in reversed(messages_in):
        if m.get("role") == "user":
            last_user = (m.get("content") or "")
            break

    symbols = extract_tickers(last_user, max_n=1)
    print(symbols)
    finnhub_bundle = None

    if symbols:
        symbol = symbols[0]
        try:
            today = date.today()
            frm = (today - timedelta(days=10)).isoformat()
            to = today.isoformat()

            # 병렬 호출
            quote, profile, metrics, news = await asyncio.gather(
                finn.quote(symbol),
                finn.profile2(symbol),
                finn.metrics(symbol),
                finn.news(symbol, frm, to),
            )

            # 뉴스 너무 길면 느려짐 → 5개로 제한
            if isinstance(news, list):
                news = news[:5]

            # profile이 유효할 때만 주입
            if isinstance(profile, dict) and profile.get("ticker"):
                finnhub_bundle = {
                    "symbol": symbol,
                    "quote": quote,
                    "profile": profile,
                    "metrics": metrics,
                    "news": news,
                }

        except Exception as e:
            # 실패 원인을 숨기지 말고 출력
            print(f"[Finnhub] fetch failed for {symbol}: {e}")
            finnhub_bundle = None

    messages = messages_in

    if finnhub_bundle:
        injected = f"""
사용자가 종목/ETF 티커를 언급했다: {finnhub_bundle["symbol"]}
아래 Finnhub 데이터만 근거로 답하라. 모르면 모른다고 말하라.
과장 금지. 추정은 '추정'으로 표시.

[Finnhub quote]
{finnhub_bundle["quote"]}

[Finnhub profile2]
{finnhub_bundle["profile"]}

[Finnhub metrics]
{finnhub_bundle["metrics"]}

[Finnhub news(최근10일, 최대5개)]
{finnhub_bundle["news"]}

[출력 형식]
1) 한줄 결론(장기/적립식 관점)
2) 펀더멘털 강점 3 (근거 포함)
3) 리스크 3 (근거 포함)
4) 액션 3 (분할매수 조건 포함)
5) 확인 질문 2
""".strip()

        messages = [
            {"role": "system", "content": "한국어로, 근거 중심으로 답하라."},
            {"role": "system", "content": injected},
            *messages
        ]

    elif symbols:
        # ✅ Finnhub 실패해도 의학/약어로 추측하는 오답 방지
        symbol = symbols[0]
        messages = [
            {"role": "system", "content": "사용자 입력의 토큰을 의학/일반 약어로 추측하지 마라. 주식/ETF 티커로 우선 해석하라."},
            {"role": "system", "content": f'사용자가 "{symbol}"를 물었다. 이것이 주식/ETF 티커라는 전제로, 무엇인지(ETF/주식), 추종지수/섹터/용도(장기 적립식 관점)를 간단히 설명하라. 정확한 확인을 위해 거래소/국가를 1줄로 질문하라.'},
            *messages
        ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "1h",
    }

    try:
        data = await client.chat(payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 호출 실패: {e}")

    msg = data.get("message") or {}
    content = msg.get("content", "")
    try:
        payload = {
            "messages": messages_in,
            "response": content,
            "model": OLLAMA_MODEL,
            "last_user": last_user,
        }
        session_name = summarize_messages(messages_in)
        save_chat_log(json.dumps(payload, ensure_ascii=True), req.session_id, session_name)
    except Exception as e:
        print(f"[DB] save failed: {e}")
    return ChatResponse(model=OLLAMA_MODEL, content=content)


# -------------------------
# Finnhub 툴 (디버그용)
# -------------------------
@app.get("/api/tools/quote")
async def tool_quote(symbol: str):
    try:
        return await finn.quote(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/tools/profile")
async def tool_profile(symbol: str):
    try:
        return await finn.profile2(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/tools/metrics")
async def tool_metrics(symbol: str):
    try:
        return await finn.metrics(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/tools/news")
async def tool_news(symbol: str, days: int = 7):
    try:
        today = date.today()
        frm = (today - timedelta(days=days)).isoformat()
        news = await finn.news(symbol, frm, today.isoformat())
        return news[:5] if isinstance(news, list) else news
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# -------------------------
# “이 종목 사도 돼?” 에이전트(직접 호출용)
# -------------------------
@app.post("/api/agent/should-i-buy", response_model=ShouldIBuyResponse)
async def should_i_buy(req: ShouldIBuyRequest):
    symbol = req.symbol.strip().upper()
    question = (req.question or "이 종목 사도 돼?").strip()

    try:
        quote = await finn.quote(symbol)
        profile = await finn.profile2(symbol)
        metrics = await finn.metrics(symbol)

        today = date.today()
        frm = (today - timedelta(days=10)).isoformat()
        news = await finn.news(symbol, frm, today.isoformat())
        if isinstance(news, list):
            news = news[:5]

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Finnhub 호출 실패: {e}")

    prompt = f"""
너는 투자 리서치 어시스턴트다.
사용자 질문: "{question}"
대상 종목: {symbol}

아래 데이터만 근거로 답하라. 모르면 모른다고 말해라.
과장 금지. 추정은 '추정'으로 표시.
투자 조언이 아니라 정보 제공이며, 마지막에 리스크 고지 1줄.

[quote]
{quote}

[profile2]
{profile}

[metrics]
{metrics}

[news(최근10일, 최대5개)]
{news}

### 요구사항 
- 한국어로 답하라.
[출력 형식]
1) 결론(한 줄): 장기/적립식 관점
2) 펀더멘털 강점 3가지 (근거 지표/사실 포함)
3) 핵심 리스크 3가지 (근거 포함)
4) 체크리스트: 지금 확인해야 할 것 5개
5) 한 문장 리스크 고지


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

    return ShouldIBuyResponse(symbol=symbol, answer=content)


# -------------------------
# 주식 분석 보고서 에이전트
# -------------------------
@app.post("/api/agent/stock-report", response_model=StockReportResponse)
async def stock_report(req: StockReportRequest):
    chat_context = load_latest_session_context(req.session_id)
    return await run_stock_report(req, finn, client, chat_context)

# backend/app/main.py (파일 상단 import에 이미 asyncio/date/timedelta 있음)

@app.get("/market")
def serve_market():
    p = FRONTEND_DIR / "market.html"
    if not p.exists():
        raise HTTPException(status_code=404, detail="frontend/market.html not found")
    return FileResponse(str(p))


@app.get("/api/market/overview")
async def market_overview(category: str = "general", news_limit: int = 12):
    # "지수 현황"은 지수 대신 ETF 프록시로 보여주는 게 Finnhub에서 가장 안정적
    symbols = [
        "IVV",  # S&P500 proxy
        "QQQ",  # Nasdaq100 proxy
        "DIA",  # Dow proxy
        "IWM",  # Russell2000 proxy
        "TLT",  # 20Y bond proxy
    ]

    async def safe_quote(sym: str):
        try:
            q = await finn.quote(sym)
            return {"symbol": sym, "quote": q}
        except Exception as e:
            return {"symbol": sym, "error": str(e)}

    async def safe_news():
        try:
            news = await finn.market_news(category=category)
            if isinstance(news, list):
                news = news[: max(1, min(int(news_limit), 30))]
            return news
        except Exception as e:
            return {"error": str(e)}

    quotes, news = await asyncio.gather(
        asyncio.gather(*[safe_quote(s) for s in symbols]),
        safe_news(),
    )

    return {"category": category, "quotes": quotes, "news": news}