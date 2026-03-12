"""통계 API 엔드포인트.

프로젝트의 evidence 데이터를 섹션별/지표별로 집계하여 기술 통계를 제공한다.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import project as project_crud
from app.db import get_db
from app.schemas.statistics import (
    IndicatorStatsRead,
    ProjectStatsRead,
    SectionStatsRead,
)
from app.services.statistics import (
    calculate_project_statistics,
    calculate_section_statistics,
)

router = APIRouter(
    prefix="/projects/{project_id}/statistics",
    tags=["statistics"],
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


def _stats_to_read(stats) -> SectionStatsRead:
    """SectionStats 데이터클래스를 Pydantic 모델로 변환."""
    return SectionStatsRead(
        section_key=stats.section_key,
        title=stats.title,
        total_numeric_count=stats.total_numeric_count,
        indicator_stats=[
            IndicatorStatsRead(
                indicator=ind.indicator,
                count=ind.count,
                mean=ind.mean,
                max_value=ind.max_value,
                min_value=ind.min_value,
                std_dev=ind.std_dev,
                unit=ind.unit,
                period_start=ind.period_start,
                period_end=ind.period_end,
            )
            for ind in stats.indicator_stats
        ],
        years_filter_applied=stats.years_filter_applied,
    )


@router.get(
    "",
    response_model=ProjectStatsRead,
    summary="전체 섹션 통계",
)
async def get_project_statistics(
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
    """프로젝트의 전체 섹션별 통계를 반환한다.

    - years_filter 미지정 시: 수질=최근 5년, 대기=최근 1년, 기타=전체 기간
    - years_filter=0: 전체 기간 (기본 필터 비활성화)
    - years_filter=N: 모든 섹션에 최근 N년 필터 적용
    """
    await _verify_project(db, project_id)

    project_stats = await calculate_project_statistics(
        db, project_id,
        years_filter=years_filter,
        aggregate_daily=aggregate_daily,
    )

    return ProjectStatsRead(
        project_id=project_stats.project_id,
        generated_at=project_stats.generated_at,
        sections=[_stats_to_read(s) for s in project_stats.sections],
        total_numeric_count=project_stats.total_numeric_count,
    )


@router.get(
    "/{section_key}",
    response_model=SectionStatsRead,
    summary="개별 섹션 통계",
)
async def get_section_statistics(
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
    """특정 섹션의 통계를 반환한다."""
    await _verify_project(db, project_id)

    stats = await calculate_section_statistics(
        db, project_id, section_key,
        years_filter=years_filter,
        aggregate_daily=aggregate_daily,
    )
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"섹션을 찾을 수 없습니다: {section_key}",
        )

    return _stats_to_read(stats)
