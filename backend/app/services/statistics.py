"""증거 데이터 통계 서비스.

프로젝트의 evidence 데이터를 섹션별/지표별로 집계하여
평균, 최대, 최소, 표준편차, 건수, 관측 기간 등 기술 통계를 산출한다.

대상: numeric_value가 있고 screening_only=False인 본 평가 데이터만.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    get_section_definition,
)

# 섹션 카테고리별 기본 연도 필터 (최근 N년만 사용)
_DEFAULT_YEARS_FILTER: dict[str, int] = {
    "water_quality": 5,  # 수질: 최근 5년
    "air_quality": 1,    # 대기: 최근 1년
}


@dataclass
class IndicatorStats:
    """지표별 기술 통계."""

    indicator: str
    count: int = 0
    mean: float | None = None
    max_value: float | None = None
    min_value: float | None = None
    std_dev: float | None = None
    unit: str | None = None
    period_start: str | None = None  # 최초 관측일 (ISO)
    period_end: str | None = None    # 최종 관측일 (ISO)


@dataclass
class SectionStats:
    """섹션별 통계 요약."""

    section_key: str
    title: str
    total_numeric_count: int = 0       # 수치 데이터 총 건수
    indicator_stats: list[IndicatorStats] = field(default_factory=list)
    years_filter_applied: int | None = None  # 적용된 연도 필터


@dataclass
class ProjectStats:
    """프로젝트 전체 통계."""

    project_id: str
    generated_at: str
    sections: list[SectionStats] = field(default_factory=list)
    total_numeric_count: int = 0


def _compute_stats(values: list[float]) -> tuple[float, float, float, float]:
    """평균, 최대, 최소, 표준편차를 계산한다."""
    n = len(values)
    mean = sum(values) / n
    max_val = max(values)
    min_val = min(values)
    if n >= 2:
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0
    return mean, max_val, min_val, std_dev


def _compute_daily_aggregates(
    rows: list[tuple[float, datetime | None]],
) -> list[float]:
    """시간별 데이터를 일평균으로 집계한다.

    observed_at가 없는 행은 그대로 단일 값으로 취급한다.
    """
    daily: dict[str, list[float]] = {}
    no_date_values: list[float] = []

    for numeric_value, observed_at in rows:
        if observed_at is not None:
            day_key = observed_at.strftime("%Y-%m-%d")
            daily.setdefault(day_key, []).append(numeric_value)
        else:
            no_date_values.append(numeric_value)

    result: list[float] = []
    for day_values in daily.values():
        result.append(sum(day_values) / len(day_values))
    result.extend(no_date_values)
    return result


async def _fetch_numeric_evidences(
    db: AsyncSession,
    project_id: uuid.UUID,
    category: str,
    years_filter: int | None = None,
) -> list[Evidence]:
    """수치 데이터가 있는 본 평가 evidence를 조회한다."""
    conditions = [
        Evidence.project_id == project_id,
        Evidence.category == category,
        Evidence.screening_only.is_(False),
        Evidence.numeric_value.isnot(None),
    ]

    if years_filter is not None and years_filter > 0:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=years_filter * 365)
        # observed_at가 NULL인 데이터는 시간필터에서 제외하지 않음 (날짜 미상 데이터 보존)
        conditions.append(
            or_(Evidence.observed_at >= cutoff, Evidence.observed_at.is_(None))
        )

    result = await db.execute(
        select(Evidence)
        .where(and_(*conditions))
        .order_by(Evidence.indicator, Evidence.observed_at.desc())
    )
    return list(result.scalars().all())


def _group_by_indicator(
    evidences: list[Evidence],
) -> dict[str, list[Evidence]]:
    """지표명 기준으로 그룹핑한다."""
    groups: dict[str, list[Evidence]] = {}
    for ev in evidences:
        groups.setdefault(ev.indicator, []).append(ev)
    return groups


def _calc_indicator_stats(
    indicator: str,
    evidences: list[Evidence],
    aggregate_daily: bool = False,
) -> IndicatorStats:
    """단일 지표의 통계를 계산한다."""
    if not evidences:
        return IndicatorStats(indicator=indicator)

    # 단위 추출 (첫 번째 evidence 기준)
    unit = next((ev.unit for ev in evidences if ev.unit), None)

    # 관측 기간
    observed_dates = [ev.observed_at for ev in evidences if ev.observed_at is not None]
    period_start = min(observed_dates).isoformat() if observed_dates else None
    period_end = max(observed_dates).isoformat() if observed_dates else None

    # 수치 값 목록
    if aggregate_daily:
        rows = [
            (ev.numeric_value, ev.observed_at)
            for ev in evidences
            if ev.numeric_value is not None
        ]
        values = _compute_daily_aggregates(rows)
    else:
        values = [
            ev.numeric_value for ev in evidences if ev.numeric_value is not None
        ]

    if not values:
        return IndicatorStats(
            indicator=indicator,
            unit=unit,
            period_start=period_start,
            period_end=period_end,
        )

    mean, max_val, min_val, std_dev = _compute_stats(values)

    return IndicatorStats(
        indicator=indicator,
        count=len(values),
        mean=round(mean, 4),
        max_value=round(max_val, 4),
        min_value=round(min_val, 4),
        std_dev=round(std_dev, 4),
        unit=unit,
        period_start=period_start,
        period_end=period_end,
    )


def _resolve_years_filter(
    category: str,
    explicit_years: int | None,
) -> int | None:
    """연도 필터 값을 결정한다.

    explicit_years가 명시되면 해당 값 사용.
    0이면 필터 비활성화.
    None이면 카테고리별 기본값 사용.
    """
    if explicit_years is not None:
        return explicit_years if explicit_years > 0 else None
    return _DEFAULT_YEARS_FILTER.get(category)


async def calculate_section_statistics(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
    years_filter: int | None = None,
    aggregate_daily: bool = False,
) -> SectionStats | None:
    """단일 섹션의 통계를 계산한다."""
    section_def = get_section_definition(section_key)
    if section_def is None:
        return None

    resolved_years = _resolve_years_filter(
        section_def.evidence_category, years_filter
    )

    evidences = await _fetch_numeric_evidences(
        db, project_id, section_def.evidence_category, resolved_years
    )

    groups = _group_by_indicator(evidences)

    indicator_stats_list: list[IndicatorStats] = []
    total_count = 0

    for indicator, ev_group in groups.items():
        stats = _calc_indicator_stats(indicator, ev_group, aggregate_daily)
        indicator_stats_list.append(stats)
        total_count += stats.count

    # 정렬: 건수 많은 순 → 지표명 순
    indicator_stats_list.sort(key=lambda s: (-s.count, s.indicator))

    return SectionStats(
        section_key=section_def.key,
        title=section_def.title,
        total_numeric_count=total_count,
        indicator_stats=indicator_stats_list,
        years_filter_applied=resolved_years,
    )


async def calculate_project_statistics(
    db: AsyncSession,
    project_id: uuid.UUID,
    years_filter: int | None = None,
    aggregate_daily: bool = False,
) -> ProjectStats:
    """프로젝트 전체의 섹션별 통계를 계산한다."""
    sections: list[SectionStats] = []
    total = 0

    for section_def in EIA_SECTIONS:
        stats = await calculate_section_statistics(
            db, project_id, section_def.key,
            years_filter=years_filter,
            aggregate_daily=aggregate_daily,
        )
        if stats is not None:
            sections.append(stats)
            total += stats.total_numeric_count

    return ProjectStats(
        project_id=str(project_id),
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        sections=sections,
        total_numeric_count=total,
    )
