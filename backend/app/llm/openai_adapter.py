"""OpenAI adapter — gpt-4o-mini를 사용하여 서술문을 보강한다.

OPENAI_API_KEY 환경변수 필요. 비용 효율적인 gpt-4o-mini 모델 사용.
API 실패 시 템플릿 서술문 그대로 반환 (fallback).
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.config import settings
from app.llm.base import BaseLLMAdapter, EnhanceInput, EnhanceResult

logger = logging.getLogger(__name__)

# 환경영향평가서 전문 작성자 시스템 프롬프트
SYSTEM_PROMPT = (
    "당신은 한국 환경영향평가서 전문 작성자입니다.\n"
    "아래 제공된 템플릿 서술문과 데이터를 바탕으로 "
    "자연스러운 환경영향평가서 문체로 재작성하세요.\n"
    "규칙:\n"
    "- 제공된 데이터에 없는 내용을 추가하지 마세요\n"
    "- 수치를 변경하지 마세요\n"
    "- 환경영향평가서의 공식적이고 객관적인 문체를 유지하세요\n"
    "- 근거 없는 판단이나 추측을 포함하지 마세요"
)


def _build_user_prompt(input_data: EnhanceInput) -> str:
    """사용자 프롬프트를 구성한다."""
    parts = [
        f"## 섹션: {input_data.section_title}",
        "",
        "### 기존 서술문",
        input_data.template_text,
    ]

    if input_data.statistics_summary:
        parts.extend(["", "### 통계 데이터", input_data.statistics_summary])

    if input_data.standards_check_summary:
        parts.extend(["", "### 환경기준 비교 결과", input_data.standards_check_summary])

    parts.extend([
        "",
        "### 요청",
        "위 데이터를 바탕으로 환경영향평가서의 공식적이고 객관적인 문체로 재작성하세요. "
        "기존 서술문의 내용과 수치를 유지하되, 문장 연결과 표현을 자연스럽게 다듬어 주세요.",
    ])

    return "\n".join(parts)


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI gpt-4o-mini 기반 LLM adapter."""

    @property
    def name(self) -> str:
        return "openai_paid"

    def is_available(self) -> bool:
        """OPENAI_API_KEY 설정 여부를 확인한다."""
        return bool(settings.OPENAI_API_KEY)

    async def enhance_narrative(self, input_data: EnhanceInput) -> EnhanceResult:
        """OpenAI API를 호출하여 서술문을 보강한다."""
        if not self.is_available():
            logger.warning("OPENAI_API_KEY가 설정되지 않아 fallback 반환")
            return self._fallback(input_data)

        try:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(input_data)},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            enhanced = response.choices[0].message.content
            if not enhanced or not enhanced.strip():
                logger.warning("OpenAI 응답이 비어있어 fallback 반환")
                return self._fallback(input_data)

            return EnhanceResult(
                enhanced_text=enhanced.strip(),
                adapter_used=self.name,
                is_fallback=False,
            )

        except Exception as e:
            logger.error("OpenAI API 호출 실패, fallback 반환: %s", e)
            return self._fallback(input_data)
