from typing import Any, Dict
import httpx

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, REQUEST_TIMEOUT_SEC

class OllamaClient:
    def __init__(self) -> None:
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    async def chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        timeout = httpx.Timeout(REQUEST_TIMEOUT_SEC)

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)

        # Ollama가 에러면 바로 텍스트로 올라오기도 함
        r.raise_for_status()
        return r.json()