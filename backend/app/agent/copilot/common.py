"""Shared runtime helpers for Investigation Copilot."""

import logging
from typing import Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from app.core.config import ENV_FILE, settings

load_dotenv(ENV_FILE, override=False)
logger = logging.getLogger(__name__)
MAX_SQL_CALLS = 3
MAX_HELIUS_CALLS = 3
MAX_OUTPUT_TOKENS = 300
MAX_ROWS = 50
MAX_QUESTION_CHARS = 1200
SQL_TIMEOUT_MS = 5000

def _emit(event_type: str, data: Any) -> str:
    return encode_sse({"type": event_type, "data": data})

def _get_llm(max_tokens: int = MAX_OUTPUT_TOKENS) -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=max_tokens,
        timeout=25,
        max_retries=1,
    )

def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
