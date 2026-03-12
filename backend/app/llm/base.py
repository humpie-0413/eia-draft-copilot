"""LLM adapter 추상 인터페이스.

모든 LLM adapter는 이 클래스를 상속하여 구현한다.
핵심 메서드: enhance_narrative — 템플릿 서술문을 자연스러운 문체로 보강한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EnhanceInput:
    """서술문 보강 요청 데이터."""

    section_key: str
    section_title: str
    template_text: str          # 기존 템플릿 서술문 (narrative_generator 출력)
    statistics_summary: str     # 통계 요약 텍스트
    standards_check_summary: str  # 환경기준 비교 요약 텍스트


@dataclass
class EnhanceResult:
    """서술문 보강 결과."""

    enhanced_text: str          # 보강된 서술문
    adapter_used: str           # 사용된 adapter 이름
    is_fallback: bool           # fallback(원본 반환)인지 여부


class BaseLLMAdapter(ABC):
    """LLM adapter 추상 기본 클래스.

    모든 adapter는 다음을 보장해야 한다:
    - 제공된 데이터에 없는 내용을 추가하지 않는다
    - 수치를 변경하지 않는다
    - API 실패 시 템플릿 서술문을 그대로 반환한다 (fallback)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """adapter 이름 (예: 'none', 'openai_paid', 'gemini_free')."""
        ...

    @abstractmethod
    async def enhance_narrative(self, input_data: EnhanceInput) -> EnhanceResult:
        """템플릿 서술문을 자연스러운 환경영향평가서 문체로 보강한다.

        Args:
            input_data: 보강에 필요한 입력 데이터

        Returns:
            보강된 서술문 결과
        """
        ...

    def is_available(self) -> bool:
        """adapter가 사용 가능한지 확인한다 (API 키 설정 여부 등)."""
        return True

    def _fallback(self, input_data: EnhanceInput) -> EnhanceResult:
        """API 실패 시 템플릿 서술문을 그대로 반환하는 fallback."""
        return EnhanceResult(
            enhanced_text=input_data.template_text,
            adapter_used=self.name,
            is_fallback=True,
        )
