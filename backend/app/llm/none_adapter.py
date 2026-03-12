"""None adapter — LLM 없이 템플릿 서술문을 그대로 반환한다.

기본값(LLM_ADAPTER=none). MVP에서 LLM 없이도 시스템이 완전히 작동해야 한다.
"""

from __future__ import annotations

from app.llm.base import BaseLLMAdapter, EnhanceInput, EnhanceResult


class NoneAdapter(BaseLLMAdapter):
    """LLM을 사용하지 않는 기본 adapter."""

    @property
    def name(self) -> str:
        return "none"

    async def enhance_narrative(self, input_data: EnhanceInput) -> EnhanceResult:
        """템플릿 서술문을 그대로 반환한다."""
        return EnhanceResult(
            enhanced_text=input_data.template_text,
            adapter_used=self.name,
            is_fallback=False,
        )
