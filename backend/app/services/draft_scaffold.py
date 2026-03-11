"""초안 뼈대 생성 서비스.

evidence 데이터를 섹션별로 분류하여 초안 뼈대 구조를 생성한다.
핵심 원칙: unsupported claim 금지 — LLM 자유 작문이 아닌 evidence 기반
근거 나열 방식으로만 텍스트를 배치한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    get_section_definition,
)


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


@dataclass
class DraftScaffold:
    """초안 뼈대 전체 구조."""

    project_id: str
    generated_at: str               # ISO 문자열
    sections: list[ScaffoldSection] = field(default_factory=list)
    total_evidence_count: int = 0


def _format_evidence_summary(
    section_def: SectionDefinition,
    entries: list[EvidenceEntry],
) -> str:
    """evidence 항목들을 근거 나열 방식 텍스트로 변환한다.

    LLM 자유 작문이 아닌, evidence 데이터를 정형화된 문장으로만 나열한다.
    """
    if not entries:
        return f"{section_def.title} 분야에 대한 수집된 증거 데이터가 없습니다."

    lines = [f"[{section_def.title}] 현황 근거 데이터 ({len(entries)}건)"]
    lines.append("")

    # 지표별 그룹핑
    indicator_groups: dict[str, list[EvidenceEntry]] = {}
    for entry in entries:
        indicator_groups.setdefault(entry.indicator, []).append(entry)

    for indicator, group in indicator_groups.items():
        lines.append(f"■ {indicator}")
        for entry in group:
            # 관측일 표시
            date_part = ""
            if entry.observed_at:
                date_part = f" (관측: {entry.observed_at[:10]})"

            # 값 + 단위 표시
            unit_part = f" {entry.unit}" if entry.unit else ""
            lines.append(f"  - 측정값: {entry.value}{unit_part}{date_part}")

        lines.append("")

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
    summary = _format_evidence_summary(section_def, entries)

    return ScaffoldSection(
        section_key=section_def.key,
        title=section_def.title,
        description=section_def.description,
        order=section_def.order,
        evidence_entries=entries,
        summary_text=summary,
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
        generated_at=datetime.utcnow().isoformat(),
        sections=sections,
        total_evidence_count=total_count,
    )
