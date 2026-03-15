"""환경기준 비교 서비스.

Post-1의 통계 결과를 환경기준과 비교하여 적합/초과 판정을 수행한다.
수질의 경우 등급 판정도 포함한다.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.env_standards import (
    ComparisonOp,
    Standard,
    WaterGrade,
    determine_water_grade,
    get_standard_for_indicator,
    get_standards_for_category,
)
from app.services.section_planner import (
    EIA_SECTIONS,
    get_section_definition,
)
from app.services.statistics import (
    IndicatorStats,
    calculate_section_statistics,
)


class CheckStatus:
    """판정 상태 상수."""

    PASS = "pass"  # 기준 이내 (적합)
    FAIL = "fail"  # 기준 초과
    NA = "na"      # 해당 기준 없음 또는 측정 데이터 없음


@dataclass
class IndicatorCheckResult:
    """개별 지표의 기준 비교 결과."""

    indicator: str
    standard_value: float | None = None   # 환경기준값
    standard_unit: str | None = None      # 기준 단위
    time_basis: str | None = None         # 시간기준 (연평균, 24시간 등)
    measured_avg: float | None = None     # 측정 평균값
    measured_max: float | None = None     # 측정 최대값
    measured_count: int = 0               # 측정 데이터 건수
    status: str = CheckStatus.NA          # 판정 (pass/fail/na)
    exceedance_rate: float | None = None  # 초과율 (%, 측정값 중 기준 초과 비율)
    description: str = ""                 # 기준 설명
    legal_basis: str = ""                 # 법적 근거 (예: "환경정책기본법 시행령 별표 제1호")


@dataclass
class SectionCheckResult:
    """섹션별 기준 비교 결과."""

    section_key: str
    title: str
    indicators: list[IndicatorCheckResult] = field(default_factory=list)
    water_grade: str | None = None       # 수질 등급 (수질 섹션에서만)
    water_grade_name: str | None = None  # 수질 등급명
    has_exceedance: bool = False         # 초과 지표 존재 여부
    exceedance_count: int = 0           # 초과 지표 수
    summary: str = ""                    # 요약 서술문


@dataclass
class ProjectCheckResult:
    """프로젝트 전체 기준 비교 결과."""

    project_id: str
    generated_at: str
    sections: list[SectionCheckResult] = field(default_factory=list)
    total_exceedance_count: int = 0      # 전체 초과 지표 수


def _check_indicator(
    stats: IndicatorStats,
    standard: Standard,
) -> IndicatorCheckResult:
    """단일 지표를 환경기준과 비교한다."""
    result = IndicatorCheckResult(
        indicator=stats.indicator,
        standard_value=standard.limit_value,
        standard_unit=standard.unit,
        time_basis=standard.time_basis,
        measured_avg=stats.mean,
        measured_max=stats.max_value,
        measured_count=stats.count,
        description=standard.description,
        legal_basis=standard.legal_basis,
    )

    if stats.mean is None or stats.count == 0 or (
        isinstance(stats.mean, float) and math.isnan(stats.mean)
    ):
        result.status = CheckStatus.NA
        return result

    # 평균 기준 판정
    if standard.op == ComparisonOp.LEQ:
        result.status = CheckStatus.PASS if stats.mean <= standard.limit_value else CheckStatus.FAIL
    elif standard.op == ComparisonOp.GEQ:
        result.status = CheckStatus.PASS if stats.mean >= standard.limit_value else CheckStatus.FAIL

    return result


def _check_indicator_no_standard(
    stats: IndicatorStats,
) -> IndicatorCheckResult:
    """환경기준이 없는 지표의 결과를 생성한다."""
    return IndicatorCheckResult(
        indicator=stats.indicator,
        measured_avg=stats.mean,
        measured_max=stats.max_value,
        measured_count=stats.count,
        status=CheckStatus.NA,
        description="해당 환경기준 없음",
    )


def _format_legal_ref(legal_basis: str) -> str:
    """법적 근거를 서술문에 삽입 가능한 형태로 변환한다.

    "법 시행령 별표 제N호 (기준명)" → "법 시행령 별표 제N호에 따른 기준명"
    """
    _CONVERSIONS: dict[str, str] = {
        "환경정책기본법 시행령 별표 제1호 (대기환경기준)":
            "환경정책기본법 시행령 별표 제1호에 따른 대기환경기준",
        "환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준) — 하천 생활환경기준":
            "환경정책기본법 시행령 별표 제1호에 따른 하천 수질 및 수생태계 생활환경기준",
        "환경정책기본법 시행령 별표 제1호 (소음환경기준)":
            "환경정책기본법 시행령 별표 제1호에 따른 소음환경기준",
        "토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)":
            "토양환경보전법 시행규칙 별표 제3호에 따른 토양오염우려기준",
    }
    return _CONVERSIONS.get(legal_basis, legal_basis)


def _generate_section_summary(
    section_key: str,
    title: str,
    results: list[IndicatorCheckResult],
    water_grade: WaterGrade | None,
) -> str:
    """섹션별 기준 비교 요약 서술문을 생성한다."""
    if not results:
        return ""

    pass_indicators = [r for r in results if r.status == CheckStatus.PASS]
    fail_indicators = [r for r in results if r.status == CheckStatus.FAIL]
    measured = [r for r in results if r.status != CheckStatus.NA]

    if not measured:
        return ""

    lines: list[str] = []

    # 수질인 경우 등급 서술 추가
    if section_key == "water_quality" and water_grade is not None:
        lines.append(
            f"수질 측정 결과, 하천 생활환경기준 {water_grade.grade}등급"
            f"({water_grade.grade_name}) 수준에 해당한다."
        )

    # 지표별 판정 서술
    for r in measured:
        if r.standard_value is None:
            continue
        unit = r.standard_unit or ""
        avg_str = f"{r.measured_avg:.4g}" if r.measured_avg is not None else "-"
        std_str = f"{r.standard_value:.4g}"
        legal_prefix = _format_legal_ref(r.legal_basis) if r.legal_basis else "환경기준"
        if r.status == CheckStatus.PASS:
            lines.append(
                f"{r.indicator} {r.time_basis or '평균'} {avg_str} {unit}으로 "
                f"{legal_prefix}({std_str} {unit}) 이내이며 적합한 수준이다."
            )
        elif r.status == CheckStatus.FAIL:
            lines.append(
                f"{r.indicator} {r.time_basis or '평균'} {avg_str} {unit}으로 "
                f"{legal_prefix}({std_str} {unit}) 초과로 저감대책 검토가 필요하다."
            )

    # 종합 판정
    if fail_indicators:
        names = ", ".join(r.indicator for r in fail_indicators)
        lines.append(f"환경기준 초과 지표: {names}.")
    elif pass_indicators:
        lines.append("전반적으로 환경기준을 만족하는 것으로 나타났다.")

    return "\n".join(lines)


async def check_section_standards(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
    years_filter: int | None = None,
    aggregate_daily: bool = False,
) -> SectionCheckResult | None:
    """단일 섹션의 환경기준 비교를 수행한다."""
    section_def = get_section_definition(section_key)
    if section_def is None:
        return None

    # 통계 계산
    section_stats = await calculate_section_statistics(
        db, project_id, section_key,
        years_filter=years_filter,
        aggregate_daily=aggregate_daily,
    )
    if section_stats is None:
        return None

    category = section_def.evidence_category
    standards = get_standards_for_category(category)

    # 환경기준이 정의된 지표를 기준으로 비교 수행
    indicator_results: list[IndicatorCheckResult] = []
    checked_indicators: set[str] = set()

    for stats in section_stats.indicator_stats:
        standard = get_standard_for_indicator(category, stats.indicator)
        if standard is not None:
            result = _check_indicator(stats, standard)
            checked_indicators.add(stats.indicator)
        else:
            result = _check_indicator_no_standard(stats)
        indicator_results.append(result)

    # 기준은 있지만 측정 데이터가 없는 지표도 추가 (na 상태)
    for std in standards:
        if std.indicator not in checked_indicators:
            # 같은 indicator 이름이 이미 있는지 확인 (중복 방지)
            already_added = any(r.indicator == std.indicator for r in indicator_results)
            if not already_added:
                indicator_results.append(IndicatorCheckResult(
                    indicator=std.indicator,
                    standard_value=std.limit_value,
                    standard_unit=std.unit,
                    time_basis=std.time_basis,
                    status=CheckStatus.NA,
                    description=f"{std.description} (측정 데이터 없음)",
                    legal_basis=std.legal_basis,
                ))

    # 초과 집계
    fail_count = sum(1 for r in indicator_results if r.status == CheckStatus.FAIL)

    # 수질 등급 판정
    water_grade: WaterGrade | None = None
    if category == "water_quality":
        # 통계에서 BOD, COD, DO, T-P 평균 추출
        avg_map: dict[str, float] = {}
        for stats in section_stats.indicator_stats:
            if stats.mean is not None and stats.indicator in ("BOD", "COD", "DO", "T-P"):
                avg_map[stats.indicator] = stats.mean
        water_grade = determine_water_grade(
            bod=avg_map.get("BOD"),
            cod=avg_map.get("COD"),
            do_val=avg_map.get("DO"),
            tp=avg_map.get("T-P"),
        )

    summary = _generate_section_summary(
        section_key, section_def.title, indicator_results, water_grade
    )

    return SectionCheckResult(
        section_key=section_def.key,
        title=section_def.title,
        indicators=indicator_results,
        water_grade=water_grade.grade if water_grade else None,
        water_grade_name=water_grade.grade_name if water_grade else None,
        has_exceedance=fail_count > 0,
        exceedance_count=fail_count,
        summary=summary,
    )


async def check_project_standards(
    db: AsyncSession,
    project_id: uuid.UUID,
    years_filter: int | None = None,
    aggregate_daily: bool = False,
) -> ProjectCheckResult:
    """프로젝트 전체의 환경기준 비교를 수행한다."""
    sections: list[SectionCheckResult] = []
    total_exceedance = 0

    for section_def in EIA_SECTIONS:
        result = await check_section_standards(
            db, project_id, section_def.key,
            years_filter=years_filter,
            aggregate_daily=aggregate_daily,
        )
        if result is not None:
            sections.append(result)
            total_exceedance += result.exceedance_count

    return ProjectCheckResult(
        project_id=str(project_id),
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        sections=sections,
        total_exceedance_count=total_exceedance,
    )
