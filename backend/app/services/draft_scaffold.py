"""초안 뼈대 생성 서비스.

evidence 데이터를 섹션별로 분류하여 초안 뼈대 구조를 생성한다.
핵심 원칙: unsupported claim 금지 — LLM 자유 작문이 아닌 evidence 기반
근거 나열 방식으로만 텍스트를 배치한다.

Post-3 개편: 서술문 → 통계 요약 테이블 → 환경기준 비교 테이블 → 상세 데이터 샘플(최대 5건)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import draft_narrative as draft_narrative_crud
from app.models.evidence import Evidence
from app.services.narrative_generator import generate_narrative
from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    calculate_section_status,
    get_section_definition,
)
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
    check_section_standards,
)
from app.services.statistics import (
    IndicatorStats,
    SectionStats,
    calculate_section_statistics,
)

# 상세 데이터 부록에 표시할 최대 샘플 건수
MAX_DETAIL_SAMPLES = 5


@dataclass
class EvidenceEntry:
    """초안 뼈대에 배치되는 개별 근거 항목."""

    evidence_id: str
    indicator: str
    value: str
    numeric_value: float | None
    unit: str | None
    observed_at: str | None      # ISO 문자열
    data_source_id: str | None
    metadata_json: dict | None


@dataclass
class ScaffoldSection:
    """초안 뼈대의 섹션 단위."""

    section_key: str
    title: str
    description: str
    order: int
    evidence_entries: list[EvidenceEntry] = field(default_factory=list)
    summary_text: str = ""          # evidence 기반 자동 생성 요약문
    narrative: str = ""             # Post-3: 서술문 템플릿 엔진 결과
    state: str = "empty"            # 섹션 상태 (output-contracts.md 스펙)
    missing_indicators: list[str] = field(default_factory=list)  # 누락된 필수 지표


@dataclass
class DraftScaffold:
    """초안 뼈대 전체 구조."""

    project_id: str
    generated_at: str               # ISO 문자열
    sections: list[ScaffoldSection] = field(default_factory=list)
    total_evidence_count: int = 0


def _format_period(start: str | None, end: str | None) -> str:
    """관측 기간 문자열을 생성한다."""
    if start and end:
        s = start[:10]
        e = end[:10]
        return f"{s}~{e}" if s != e else s
    if start:
        return start[:10]
    if end:
        return end[:10]
    return "-"


def _format_stats_summary(
    section_def: SectionDefinition,
    entries: list[EvidenceEntry],
    indicator_stats: list[IndicatorStats],
    check_results: list[IndicatorCheckResult] | None = None,
) -> str:
    """통계 요약 테이블 + 환경기준 비교 테이블 + 상세 데이터 샘플 텍스트를 생성한다.

    Post-3 개편: 서술문 제거 (narrative 필드로 분리), 구조 정리
    """
    if not entries:
        return ""

    lines: list[str] = []

    # 환경기준 비교 결과를 지표명 기준 딕셔너리로 구성
    check_map: dict[str, IndicatorCheckResult] = {}
    if check_results:
        for cr in check_results:
            check_map[cr.indicator] = cr
    has_standards = bool(check_map)

    # ── 1. 측정 현황 요약 (통계 테이블) ──
    stats_with_data = [s for s in indicator_stats if s.count > 0]
    if stats_with_data:
        lines.append(f"[측정 현황 요약] ({len(entries)}건 기준)")
        lines.append("")

        if has_standards:
            lines.append("지표명 | 평균 | 최대 | 최소 | 건수 | 환경기준 | 판정 | 기간")
            lines.append("--- | --- | --- | --- | --- | --- | --- | ---")
        else:
            lines.append("지표명 | 평균 | 최대 | 최소 | 건수 | 기간")
            lines.append("--- | --- | --- | --- | --- | ---")

        for s in stats_with_data:
            unit_suffix = f" {s.unit}" if s.unit else ""
            mean_str = f"{s.mean}{unit_suffix}" if s.mean is not None else "-"
            max_str = f"{s.max_value}{unit_suffix}" if s.max_value is not None else "-"
            min_str = f"{s.min_value}{unit_suffix}" if s.min_value is not None else "-"
            period = _format_period(s.period_start, s.period_end)

            if has_standards:
                cr = check_map.get(s.indicator)
                if cr and cr.standard_value is not None:
                    std_unit = cr.standard_unit or ""
                    std_str = f"{cr.standard_value:.4g} {std_unit}".strip()
                    status_str = "적합" if cr.status == CheckStatus.PASS else (
                        "초과" if cr.status == CheckStatus.FAIL else "-"
                    )
                else:
                    std_str = "-"
                    status_str = "-"
                lines.append(
                    f"{s.indicator} | {mean_str} | {max_str} | {min_str} | "
                    f"{s.count} | {std_str} | {status_str} | {period}"
                )
            else:
                lines.append(
                    f"{s.indicator} | {mean_str} | {max_str} | {min_str} | {s.count} | {period}"
                )
        lines.append("")

    # 비수치 데이터는 별도 나열
    numeric_indicators = {s.indicator for s in stats_with_data}
    non_numeric_entries = [e for e in entries if e.indicator not in numeric_indicators]
    if non_numeric_entries:
        non_numeric_groups: dict[str, list[EvidenceEntry]] = {}
        for entry in non_numeric_entries:
            non_numeric_groups.setdefault(entry.indicator, []).append(entry)

        lines.append(f"[비수치 데이터] ({len(non_numeric_entries)}건)")
        lines.append("")
        for indicator, group in non_numeric_groups.items():
            lines.append(f"■ {indicator}")
            for entry in group:
                date_part = f" (관측: {entry.observed_at[:10]})" if entry.observed_at else ""
                lines.append(f"  - {entry.value}{date_part}")
            lines.append("")

    # ── 2. 상세 데이터 샘플 (최대 5건) ──
    sample_count = min(len(entries), MAX_DETAIL_SAMPLES)
    lines.append(f"[측정 데이터] (대표 {sample_count}건)")
    lines.append("")

    sample_entries = entries[:MAX_DETAIL_SAMPLES]
    for entry in sample_entries:
        date_part = f" (관측: {entry.observed_at[:10]})" if entry.observed_at else ""
        unit_part = f" {entry.unit}" if entry.unit else ""
        lines.append(f"  - {entry.indicator}: {entry.value}{unit_part}{date_part}")

    if len(entries) > MAX_DETAIL_SAMPLES:
        lines.append(f"  ... 외 {len(entries) - MAX_DETAIL_SAMPLES}건은 별첨 참조")

    return "\n".join(lines)


async def _fetch_section_evidences(
    db: AsyncSession,
    project_id: uuid.UUID,
    category: str,
) -> list[Evidence]:
    """섹션에 해당하는 본 평가 evidence를 조회한다."""
    result = await db.execute(
        select(Evidence)
        .where(
            (Evidence.project_id == project_id)
            & (Evidence.category == category)
            & (Evidence.screening_only.is_(False))
        )
        .order_by(Evidence.indicator, Evidence.observed_at.desc())
    )
    return list(result.scalars().all())


def _evidence_to_entry(ev: Evidence) -> EvidenceEntry:
    """ORM Evidence 객체를 EvidenceEntry로 변환한다."""
    return EvidenceEntry(
        evidence_id=str(ev.id),
        indicator=ev.indicator,
        value=ev.value,
        numeric_value=ev.numeric_value,
        unit=ev.unit,
        observed_at=ev.observed_at.isoformat() if ev.observed_at else None,
        data_source_id=str(ev.data_source_id) if ev.data_source_id else None,
        metadata_json=ev.metadata_json,
    )


async def generate_section_scaffold(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
) -> ScaffoldSection | None:
    """단일 섹션의 초안 뼈대를 생성한다."""
    section_def = get_section_definition(section_key)
    if section_def is None:
        return None

    evidences = await _fetch_section_evidences(
        db, project_id, section_def.evidence_category
    )

    entries = [_evidence_to_entry(ev) for ev in evidences]

    # 통계 계산 (기본 필터 적용)
    section_stats = await calculate_section_statistics(
        db, project_id, section_key
    )
    indicator_stats = section_stats.indicator_stats if section_stats else []

    # 환경기준 비교 (기본 필터 적용)
    section_check = await check_section_standards(db, project_id, section_key)
    check_results = section_check.indicators if section_check else None

    # 서술문 생성: LLM 보강 서술문이 있으면 우선 사용, 없으면 템플릿 생성 (Post-3)
    saved_narrative = await draft_narrative_crud.get_narrative(
        db, project_id, section_key
    )
    if saved_narrative:
        narrative = saved_narrative.narrative_text
    else:
        narrative = generate_narrative(section_def, section_stats, section_check)

    # 통계 요약 테이블 + 상세 데이터 샘플
    summary = _format_stats_summary(
        section_def, entries, indicator_stats,
        check_results=check_results,
    )

    # 섹션 상태 조회하여 state, missing_indicators 반영
    section_status = await calculate_section_status(db, project_id, section_key)
    state = section_status.status if section_status else "empty"
    missing = section_status.missing_indicators if section_status else []

    return ScaffoldSection(
        section_key=section_def.key,
        title=section_def.title,
        description=section_def.description,
        order=section_def.order,
        evidence_entries=entries,
        summary_text=summary,
        narrative=narrative,
        state=state,
        missing_indicators=missing,
    )


async def generate_draft_scaffold(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> DraftScaffold:
    """프로젝트의 전체 초안 뼈대를 생성한다.

    모든 섹션에 대해 evidence를 수집하고 근거 텍스트를 배치한다.
    """
    sections = []
    total_count = 0

    for section_def in EIA_SECTIONS:
        scaffold = await generate_section_scaffold(
            db, project_id, section_def.key
        )
        if scaffold is not None:
            sections.append(scaffold)
            total_count += len(scaffold.evidence_entries)

    return DraftScaffold(
        project_id=str(project_id),
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        sections=sections,
        total_evidence_count=total_count,
    )
