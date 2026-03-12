"""환경기준 비교 API 엔드포인트.

프로젝트의 측정 데이터를 환경기준과 비교하여 적합/초과 판정 결과를 제공한다.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import project as project_crud
from app.db import get_db
from app.schemas.standards import (
    IndicatorCheckRead,
    ProjectCheckRead,
    SectionCheckRead,
)
from app.services.standard_checker import (
    check_project_standards,
    check_section_standards,
)

router = APIRouter(
    prefix="/projects/{project_id}/standards-check",
    tags=["standards-check"],
)


async def _verify_project(db: AsyncSession, project_id: uuid.UUID):
    """프로젝트 존재 여부를 확인한다."""
    project = await project_crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )
    return project


def _section_to_read(result) -> SectionCheckRead:
    """SectionCheckResult 데이터클래스를 Pydantic 모델로 변환."""
    return SectionCheckRead(
        section_key=result.section_key,
        title=result.title,
        indicators=[
            IndicatorCheckRead(
                indicator=ind.indicator,
                standard_value=ind.standard_value,
                standard_unit=ind.standard_unit,
                time_basis=ind.time_basis,
                measured_avg=ind.measured_avg,
                measured_max=ind.measured_max,
                measured_count=ind.measured_count,
                status=ind.status,
                exceedance_rate=ind.exceedance_rate,
                description=ind.description,
            )
            for ind in result.indicators
        ],
        water_grade=result.water_grade,
        water_grade_name=result.water_grade_name,
        has_exceedance=result.has_exceedance,
        exceedance_count=result.exceedance_count,
        summary=result.summary,
    )


@router.get(
    "",
    response_model=ProjectCheckRead,
    summary="전체 섹션 환경기준 비교",
)
async def get_project_standards_check(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    years_filter: int | None = Query(
        None,
        description="연도 필터 (0=전체 기간, None=카테고리별 기본값, N=최근 N년)",
    ),
    aggregate_daily: bool = Query(
        False,
        description="시간별 데이터를 일평균으로 집계 여부",
    ),
):
    """프로젝트의 전체 섹션별 환경기준 비교 결과를 반환한다."""
    await _verify_project(db, project_id)

    result = await check_project_standards(
        db, project_id,
        years_filter=years_filter,
        aggregate_daily=aggregate_daily,
    )

    return ProjectCheckRead(
        project_id=result.project_id,
        generated_at=result.generated_at,
        sections=[_section_to_read(s) for s in result.sections],
        total_exceedance_count=result.total_exceedance_count,
    )


@router.get(
    "/{section_key}",
    response_model=SectionCheckRead,
    summary="개별 섹션 환경기준 비교",
)
async def get_section_standards_check(
    project_id: uuid.UUID,
    section_key: str,
    db: AsyncSession = Depends(get_db),
    years_filter: int | None = Query(
        None,
        description="연도 필터 (0=전체 기간, None=카테고리별 기본값, N=최근 N년)",
    ),
    aggregate_daily: bool = Query(
        False,
        description="시간별 데이터를 일평균으로 집계 여부",
    ),
):
    """특정 섹션의 환경기준 비교 결과를 반환한다."""
    await _verify_project(db, project_id)

    result = await check_section_standards(
        db, project_id, section_key,
        years_filter=years_filter,
        aggregate_daily=aggregate_daily,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"섹션을 찾을 수 없습니다: {section_key}",
        )

    return _section_to_read(result)
