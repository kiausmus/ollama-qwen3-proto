from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ollama /api/chat messages 형식"
    )
    session_id: str

class ChatResponse(BaseModel):
    model: str
    content: str

class ShouldIBuyRequest(BaseModel):
    symbol: str
    question: Optional[str] = "이 종목 사도 돼? 장기 관점으로"

class ShouldIBuyResponse(BaseModel):
    symbol: str
    answer: str

class StockReportRequest(BaseModel):
    symbol: Optional[str] = None
    session_id: Optional[str] = None
    audience: Optional[str] = "장기 투자자"
    focus: Optional[str] = "펀더멘털 중심"

class StockReportResponse(BaseModel):
    symbol: str
    report: str

class SessionSummary(BaseModel):
    id: str
    name: str
    updated_at: datetime

class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]

class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]

class ReportViewResponse(BaseModel):
    session_id: str
    
    report: Optional[str] = None
    report_chat_id: Optional[int] = None
    latest_chat_id: Optional[int] = None
