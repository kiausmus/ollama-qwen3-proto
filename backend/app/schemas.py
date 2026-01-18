from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ollama /api/chat messages 형식"
    )

class ChatResponse(BaseModel):
    model: str
    content: str

class ShouldIBuyRequest(BaseModel):
    symbol: str
    question: Optional[str] = "이 종목 사도 돼? 장기 관점으로"

class ShouldIBuyResponse(BaseModel):
    symbol: str
    answer: str