from typing import Any, Dict, List, Optional
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
    symbol: str
    session_id: str
    audience: Optional[str] = "장기 투자자"
    focus: Optional[str] = "펀더멘털 중심"

class StockReportResponse(BaseModel):
    symbol: str
    report: str
