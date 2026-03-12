"""LLM adapter 상태 및 서술문 보강 API 엔드포인트."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud import project as project_crud
from app.db import get_db
from app.llm import get_llm_adapter
from app.llm.base import EnhanceInput
from app.services.draft_scaffold import generate_section_scaffold
from app.services.narrative_generator import generate_narrative
from app.services.section_planner import get_section_definition
from app.services.standard_checker import check_section_standards
from app.services.statistics import calculate_section_statistics

router = APIRouter(prefix="/llm", tags=["llm"])


# ────────────────────────────────────────────
# 응답 스키마
# ────────────────────────────────────────────

class LLMStatusResponse(BaseModel):
    """LLM adapter 상태 응답."""
    adapter: str = Field(..., description="현재 활성 adapter (none|openai_paid|gemini_free)")
    available: bool = Field(..., description="adapter 사용 가능 여부 (API 키 설정 등)")
    openai_key_set: bool = Field(..., description="OPENAI_API_KEY 설정 여부")
    google_key_set: bool = Field(..., description="GOOGLE_API_KEY 설정 여부")


class EnhanceRequest(BaseModel):
    """서술문 보강 요청."""
    section_key: str = Field(..., description="보강할 섹션 키")


class EnhanceResponse(BaseModel):
    """서술문 보강 응답."""
    section_key: str
    original_narrative: str = Field(..., description="원본 템플릿 서술문")
    enhanced_narrative: str = Field(..., description="보강된 서술문")
    adapter_used: str = Field(..., description="사용된 adapter")
    is_fallback: bool = Field(..., description="fallback 여부 (API 실패 시 원본 반환)")


# ────────────────────────────────────────────
# 엔드포인트
# ────────────────────────────────────────────

@router.get(
    "/status",
    response_model=LLMStatusResponse,
    summary="LLM adapter 상태 조회",
)
async def get_llm_status():
    """현재 LLM adapter 설정 및 API 키 상태를 반환한다."""
    adapter = get_llm_adapter()
    return LLMStatusResponse(
        adapter=adapter.name,
        available=adapter.is_available(),
        openai_key_set=bool(settings.OPENAI_API_KEY),
        google_key_set=bool(settings.GOOGLE_API_KEY),
    )


@router.post(
    "/projects/{project_id}/enhance",
    response_model=EnhanceResponse,
    summary="섹션 서술문 AI 보강",
)
async def enhance_section_narrative(
    project_id: uuid.UUID,
    body: EnhanceRequest,
    db: AsyncSession = Depends(get_db),
):
    """특정 섹션의 서술문을 LLM으로 보강한다.

    기존 템플릿 서술문을 유지하면서 자연스러운 문체로 다듬는다.
    LLM_ADAPTER=none이면 원본 그대로 반환한다.
    """
    # 프로젝트 확인
    project = await project_crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )

    section_def = get_section_definition(body.section_key)
    if section_def is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"섹션을 찾을 수 없습니다: {body.section_key}",
        )

    # 통계 및 기준비교 데이터 수집
    section_stats = await calculate_section_statistics(
        db, project_id, body.section_key
    )
    section_check = await check_section_standards(
        db, project_id, body.section_key
    )

    # 원본 서술문 생성
    original_narrative = generate_narrative(section_def, section_stats, section_check)

    # 통계 요약 텍스트 구성
    stats_summary = ""
    if section_stats and section_stats.indicator_stats:
        parts = []
        for s in section_stats.indicator_stats:
            if s.count > 0:
                unit = f" {s.unit}" if s.unit else ""
                parts.append(f"{s.indicator}: 평균 {s.mean}{unit}, 최대 {s.max_value}{unit}, 최소 {s.min_value}{unit} ({s.count}건)")
        stats_summary = "\n".join(parts)

    # 환경기준 비교 요약 텍스트 구성
    check_summary = ""
    if section_check and section_check.indicators:
        parts = []
        for r in section_check.indicators:
            if r.standard_value is not None:
                std_unit = r.standard_unit or ""
                status_text = "적합" if r.status == "pass" else ("초과" if r.status == "fail" else "-")
                parts.append(
                    f"{r.indicator}: 기준 {r.standard_value} {std_unit}, "
                    f"측정 평균 {r.measured_avg}, 판정 {status_text}"
                )
        check_summary = "\n".join(parts)

    # LLM 보강
    adapter = get_llm_adapter()
    enhance_input = EnhanceInput(
        section_key=body.section_key,
        section_title=section_def.title,
        template_text=original_narrative,
        statistics_summary=stats_summary,
        standards_check_summary=check_summary,
    )

    result = await adapter.enhance_narrative(enhance_input)

    return EnhanceResponse(
        section_key=body.section_key,
        original_narrative=original_narrative,
        enhanced_narrative=result.enhanced_text,
        adapter_used=result.adapter_used,
        is_fallback=result.is_fallback,
    )
