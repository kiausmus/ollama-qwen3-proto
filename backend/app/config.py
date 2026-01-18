import os
from dotenv import load_dotenv

# 프로젝트 루트의 .env 사용 가능하게 (없어도 동작)
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
REQUEST_TIMEOUT_SEC = float(os.getenv("OLLAMA_TIMEOUT", "600"))

# Finnhub
FINNHUB_BASE_URL = os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1").rstrip("/")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "d5m3rt1r01qidp4jpc4gd5m3rt1r01qidp4jpc50").strip()