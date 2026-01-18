import time
from typing import Any, Dict, Optional, Tuple
import httpx

from .config import FINNHUB_BASE_URL, FINNHUB_API_KEY, REQUEST_TIMEOUT_SEC

class SimpleTTLCache:
    def __init__(self):
        self.store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str):
        v = self.store.get(key)
        if not v:
            return None
        exp, data = v
        if time.time() > exp:
            self.store.pop(key, None)
            return None
        return data

    def set(self, key: str, data: Any, ttl_sec: int):
        self.store[key] = (time.time() + ttl_sec, data)

_cache = SimpleTTLCache()

class FinnhubClient:
    def __init__(self) -> None:
        if not FINNHUB_API_KEY:
            raise RuntimeError("FINNHUB_API_KEY가 비어있음(.env 확인)")
        self.base = FINNHUB_BASE_URL.rstrip("/")
        self.key = FINNHUB_API_KEY

    async def _get(self, path: str, params: Dict[str, Any], ttl: Optional[int] = None) -> Any:
        url = f"{self.base}{path}"
        params = dict(params)
        params["token"] = self.key

        cache_key = None
        if ttl:
            cache_key = f"{path}|{sorted(params.items())}"
            hit = _cache.get(cache_key)
            if hit is not None:
                return hit

        timeout = httpx.Timeout(REQUEST_TIMEOUT_SEC)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, params=params)

        if r.status_code != 200:
            raise RuntimeError(f"Finnhub 오류 {r.status_code}: {r.text}")

        data = r.json()
        if ttl and cache_key:
            _cache.set(cache_key, data, ttl)
        return data

    async def quote(self, symbol: str) -> Any:
        return await self._get("/quote", {"symbol": symbol}, ttl=15)

    async def profile2(self, symbol: str) -> Any:
        return await self._get("/stock/profile2", {"symbol": symbol}, ttl=3600)

    async def metrics(self, symbol: str) -> Any:
        return await self._get("/stock/metric", {"symbol": symbol, "metric": "all"}, ttl=3600)

    async def news(self, symbol: str, _from: str, to: str) -> Any:
        return await self._get("/company-news", {"symbol": symbol, "from": _from, "to": to}, ttl=300)