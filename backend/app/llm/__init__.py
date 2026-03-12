"""LLM adapter 패키지.

환경변수 LLM_ADAPTER에 따라 적절한 adapter를 반환한다.
기본값은 none (LLM 없이 템플릿 서술문 그대로 반환).
"""

from __future__ import annotations

from app.config import settings
from app.llm.base import BaseLLMAdapter


def get_llm_adapter() -> BaseLLMAdapter:
    """설정된 LLM_ADAPTER에 따라 adapter 인스턴스를 반환한다."""
    mode = settings.LLM_ADAPTER.lower()

    if mode == "openai_paid":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter()
    elif mode == "gemini_free":
        from app.llm.gemini_adapter import GeminiAdapter
        return GeminiAdapter()
    else:
        from app.llm.none_adapter import NoneAdapter
        return NoneAdapter()
