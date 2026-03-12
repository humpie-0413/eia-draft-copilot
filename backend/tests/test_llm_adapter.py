"""LLM adapter 테스트.

none/openai/gemini adapter의 동작, fallback, factory 함수를 검증한다.
실제 API 호출 없이 mock으로 테스트한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import EnhanceInput, EnhanceResult
from app.llm.none_adapter import NoneAdapter
from app.llm.openai_adapter import OpenAIAdapter, _build_user_prompt
from app.llm.gemini_adapter import GeminiAdapter, _build_user_prompt as _build_gemini_prompt


# ────────────────────────────────────────────
# 헬퍼: 테스트용 입력 데이터
# ────────────────────────────────────────────

def _make_enhance_input(
    section_key: str = "air_quality",
    section_title: str = "대기질",
    template_text: str = "본 사업지역 인근의 대기질 현황을 분석한 결과, 총 20건의 측정 데이터를 수집하였다.",
    statistics_summary: str = "PM10_연평균: 평균 45.0 ug/m3, 최대 67.5 ug/m3, 최소 22.5 ug/m3 (10건)",
    standards_check_summary: str = "PM10_연평균: 기준 50.0 ug/m3, 측정 평균 45.0, 판정 적합",
) -> EnhanceInput:
    return EnhanceInput(
        section_key=section_key,
        section_title=section_title,
        template_text=template_text,
        statistics_summary=statistics_summary,
        standards_check_summary=standards_check_summary,
    )


# ────────────────────────────────────────────
# None Adapter 테스트
# ────────────────────────────────────────────

class TestNoneAdapter:
    @pytest.mark.asyncio
    async def test_returns_template_as_is(self):
        """none adapter는 템플릿 서술문을 그대로 반환한다."""
        adapter = NoneAdapter()
        input_data = _make_enhance_input()

        result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.adapter_used == "none"
        assert result.is_fallback is False

    def test_name(self):
        adapter = NoneAdapter()
        assert adapter.name == "none"

    def test_is_available(self):
        adapter = NoneAdapter()
        assert adapter.is_available() is True

    @pytest.mark.asyncio
    async def test_empty_template(self):
        """빈 템플릿도 그대로 반환한다."""
        adapter = NoneAdapter()
        input_data = _make_enhance_input(template_text="")

        result = await adapter.enhance_narrative(input_data)
        assert result.enhanced_text == ""


# ────────────────────────────────────────────
# OpenAI Adapter 테스트
# ────────────────────────────────────────────

class TestOpenAIAdapter:
    def test_name(self):
        adapter = OpenAIAdapter()
        assert adapter.name == "openai_paid"

    def test_is_available_with_key(self):
        """API 키가 설정되면 사용 가능"""
        with patch.object(OpenAIAdapter, "is_available", return_value=True):
            adapter = OpenAIAdapter()
            assert adapter.is_available() is True

    def test_is_not_available_without_key(self):
        """API 키가 없으면 사용 불가"""
        with patch.object(OpenAIAdapter, "is_available", return_value=False):
            adapter = OpenAIAdapter()
            assert adapter.is_available() is False

    @pytest.mark.asyncio
    async def test_fallback_when_no_key(self):
        """API 키가 없으면 fallback 반환"""
        adapter = OpenAIAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=False):
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True
        assert result.adapter_used == "openai_paid"

    @pytest.mark.asyncio
    async def test_successful_enhance(self):
        """API 호출 성공 시 보강된 텍스트 반환"""
        mock_choice = MagicMock()
        mock_choice.message.content = "보강된 환경영향평가서 서술문입니다."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        adapter = OpenAIAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.openai_adapter.AsyncOpenAI", return_value=mock_client), \
             patch("app.llm.openai_adapter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == "보강된 환경영향평가서 서술문입니다."
        assert result.adapter_used == "openai_paid"
        assert result.is_fallback is False

    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self):
        """API 호출 실패 시 fallback 반환"""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API 오류"))

        adapter = OpenAIAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.openai_adapter.AsyncOpenAI", return_value=mock_client), \
             patch("app.llm.openai_adapter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True

    @pytest.mark.asyncio
    async def test_fallback_on_empty_response(self):
        """API 응답이 빈 문자열이면 fallback 반환"""
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        adapter = OpenAIAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.openai_adapter.AsyncOpenAI", return_value=mock_client), \
             patch("app.llm.openai_adapter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True

    def test_build_user_prompt_includes_all_sections(self):
        """사용자 프롬프트에 모든 섹션이 포함되는지 확인"""
        input_data = _make_enhance_input()
        prompt = _build_user_prompt(input_data)

        assert "대기질" in prompt
        assert "기존 서술문" in prompt
        assert "통계 데이터" in prompt
        assert "환경기준 비교 결과" in prompt
        assert input_data.template_text in prompt

    def test_build_user_prompt_without_optional_data(self):
        """통계/기준비교 없이도 프롬프트 구성 가능"""
        input_data = _make_enhance_input(
            statistics_summary="",
            standards_check_summary="",
        )
        prompt = _build_user_prompt(input_data)

        assert "기존 서술문" in prompt
        assert "통계 데이터" not in prompt
        assert "환경기준 비교 결과" not in prompt


# ────────────────────────────────────────────
# Gemini Adapter 테스트
# ────────────────────────────────────────────

class TestGeminiAdapter:
    def test_name(self):
        adapter = GeminiAdapter()
        assert adapter.name == "gemini_free"

    def test_is_available_with_key(self):
        with patch.object(GeminiAdapter, "is_available", return_value=True):
            adapter = GeminiAdapter()
            assert adapter.is_available() is True

    def test_is_not_available_without_key(self):
        with patch.object(GeminiAdapter, "is_available", return_value=False):
            adapter = GeminiAdapter()
            assert adapter.is_available() is False

    @pytest.mark.asyncio
    async def test_fallback_when_no_key(self):
        """API 키가 없으면 fallback 반환"""
        adapter = GeminiAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=False):
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True
        assert result.adapter_used == "gemini_free"

    @pytest.mark.asyncio
    async def test_successful_enhance(self):
        """API 호출 성공 시 보강된 텍스트 반환"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini가 보강한 서술문입니다."}]
                    }
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        adapter = GeminiAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.gemini_adapter.httpx.AsyncClient", return_value=mock_client), \
             patch("app.llm.gemini_adapter.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = "test-google-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == "Gemini가 보강한 서술문입니다."
        assert result.adapter_used == "gemini_free"
        assert result.is_fallback is False

    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self):
        """API 호출 실패 시 fallback 반환"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("네트워크 오류"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        adapter = GeminiAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.gemini_adapter.httpx.AsyncClient", return_value=mock_client), \
             patch("app.llm.gemini_adapter.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = "test-google-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True

    @pytest.mark.asyncio
    async def test_fallback_on_empty_candidates(self):
        """Gemini 응답에 candidates가 없으면 fallback"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"candidates": []}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        adapter = GeminiAdapter()
        input_data = _make_enhance_input()

        with patch.object(adapter, "is_available", return_value=True), \
             patch("app.llm.gemini_adapter.httpx.AsyncClient", return_value=mock_client), \
             patch("app.llm.gemini_adapter.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = "test-google-key"
            result = await adapter.enhance_narrative(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True

    def test_build_user_prompt(self):
        """Gemini 프롬프트에도 모든 섹션이 포함되는지 확인"""
        input_data = _make_enhance_input()
        prompt = _build_gemini_prompt(input_data)

        assert "대기질" in prompt
        assert "기존 서술문" in prompt
        assert input_data.template_text in prompt


# ────────────────────────────────────────────
# Factory 함수 테스트
# ────────────────────────────────────────────

class TestGetLLMAdapter:
    def test_default_returns_none_adapter(self):
        """기본값은 NoneAdapter"""
        with patch("app.llm.settings") as mock_settings:
            mock_settings.LLM_ADAPTER = "none"
            from app.llm import get_llm_adapter
            adapter = get_llm_adapter()
            assert isinstance(adapter, NoneAdapter)

    def test_openai_adapter(self):
        """openai_paid → OpenAIAdapter"""
        with patch("app.llm.settings") as mock_settings:
            mock_settings.LLM_ADAPTER = "openai_paid"
            from app.llm import get_llm_adapter
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)

    def test_gemini_adapter(self):
        """gemini_free → GeminiAdapter"""
        with patch("app.llm.settings") as mock_settings:
            mock_settings.LLM_ADAPTER = "gemini_free"
            from app.llm import get_llm_adapter
            adapter = get_llm_adapter()
            assert isinstance(adapter, GeminiAdapter)

    def test_unknown_adapter_defaults_to_none(self):
        """알 수 없는 값이면 NoneAdapter"""
        with patch("app.llm.settings") as mock_settings:
            mock_settings.LLM_ADAPTER = "unknown_model"
            from app.llm import get_llm_adapter
            adapter = get_llm_adapter()
            assert isinstance(adapter, NoneAdapter)

    def test_case_insensitive(self):
        """대소문자 구분 없이 동작"""
        with patch("app.llm.settings") as mock_settings:
            mock_settings.LLM_ADAPTER = "OPENAI_PAID"
            from app.llm import get_llm_adapter
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)


# ────────────────────────────────────────────
# BaseLLMAdapter 인터페이스 테스트
# ────────────────────────────────────────────

class TestBaseLLMAdapter:
    def test_fallback_method(self):
        """_fallback은 템플릿 서술문을 그대로 반환"""
        adapter = NoneAdapter()
        input_data = _make_enhance_input()
        result = adapter._fallback(input_data)

        assert result.enhanced_text == input_data.template_text
        assert result.is_fallback is True
        assert result.adapter_used == "none"

    def test_enhance_input_dataclass(self):
        """EnhanceInput 데이터클래스 검증"""
        input_data = _make_enhance_input()
        assert input_data.section_key == "air_quality"
        assert input_data.section_title == "대기질"
        assert "대기질 현황" in input_data.template_text

    def test_enhance_result_dataclass(self):
        """EnhanceResult 데이터클래스 검증"""
        result = EnhanceResult(
            enhanced_text="보강된 텍스트",
            adapter_used="test",
            is_fallback=False,
        )
        assert result.enhanced_text == "보강된 텍스트"
        assert result.adapter_used == "test"
        assert result.is_fallback is False
