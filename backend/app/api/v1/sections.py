"""섹션 플래너 및 초안 뼈대 API 엔드포인트.

섹션 상태 조회와 evidence 기반 초안 뼈대 생성을 제공한다.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import project as project_crud
from app.db import get_db
from app.schemas.section import (
    DraftScaffoldRead,
    EvidenceEntryRead,
    IndicatorStatusRead,
    ScaffoldSectionRead,
    SectionDefinitionRead,
    SectionStatusList,
    SectionStatusRead,
)
from app.services.draft_scaffold import (
    generate_draft_scaffold,
    generate_section_scaffold,
)
from app.services.section_planner import (
    calculate_all_sections_status,
    calculate_section_status,
    get_section_definitions,
)

router = APIRouter(
    prefix="/projects/{project_id}/sections",
    tags=["sections"],
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


# ────────────────────────────────────────────
# 섹션 정의 조회
# ────────────────────────────────────────────

@router.get(
    "/definitions",
    response_model=list[SectionDefinitionRead],
    summary="섹션 정의 목록",
)
async def list_section_definitions():
    """환경영향평가서 섹션 정의 목록을 반환한다."""
    defs = get_section_definitions()
    return [
        SectionDefinitionRead(
            key=d.key,
            title=d.title,
            description=d.description,
            evidence_category=d.evidence_category,
            required_indicators=list(d.required_indicators),
            order=d.order,
        )
        for d in defs
    ]


# ────────────────────────────────────────────
# 섹션 상태 조회
# ────────────────────────────────────────────

@router.get(
    "/status",
    response_model=SectionStatusList,
    summary="전체 섹션 상태",
)
async def get_all_sections_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트의 전체 섹션 증거 충족 상태를 반환한다."""
    await _verify_project(db, project_id)

    statuses = await calculate_all_sections_status(db, project_id)
    return SectionStatusList(
        project_id=str(project_id),
        sections=[
            SectionStatusRead(
                section_key=s.section_key,
                title=s.title,
                description=s.description,
                order=s.order,
                total_evidence_count=s.total_evidence_count,
                required_indicators=[
                    IndicatorStatusRead(
                        name=ind.name,
                        fulfilled=ind.fulfilled,
                        evidence_count=ind.evidence_count,
                    )
                    for ind in s.required_indicators
                ],
                fulfilled_count=s.fulfilled_count,
                required_count=s.required_count,
                coverage_ratio=s.coverage_ratio,
                status=s.status,
            )
            for s in statuses
        ],
        total_sections=len(statuses),
    )


@router.get(
    "/status/{section_key}",
    response_model=SectionStatusRead,
    summary="개별 섹션 상태",
)
async def get_section_status(
    project_id: uuid.UUID,
    section_key: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 섹션의 증거 충족 상태를 반환한다."""
    await _verify_project(db, project_id)

    section_status = await calculate_section_status(db, project_id, section_key)
    if section_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"섹션을 찾을 수 없습니다: {section_key}",
        )

    return SectionStatusRead(
        section_key=section_status.section_key,
        title=section_status.title,
        description=section_status.description,
        order=section_status.order,
        total_evidence_count=section_status.total_evidence_count,
        required_indicators=[
            IndicatorStatusRead(
                name=ind.name,
                fulfilled=ind.fulfilled,
                evidence_count=ind.evidence_count,
            )
            for ind in section_status.required_indicators
        ],
        fulfilled_count=section_status.fulfilled_count,
        required_count=section_status.required_count,
        coverage_ratio=section_status.coverage_ratio,
        status=section_status.status,
    )


# ────────────────────────────────────────────
# 초안 뼈대 생성
# ────────────────────────────────────────────

@router.get(
    "/scaffold",
    response_model=DraftScaffoldRead,
    summary="전체 초안 뼈대",
)
async def get_draft_scaffold(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """evidence 기반으로 전체 초안 뼈대를 생성한다.

    LLM 자유 작문이 아닌 evidence 근거 나열 방식으로 뼈대를 구성한다.
    """
    await _verify_project(db, project_id)

    scaffold = await generate_draft_scaffold(db, project_id)
    return DraftScaffoldRead(
        project_id=scaffold.project_id,
        generated_at=scaffold.generated_at,
        sections=[
            ScaffoldSectionRead(
                section_key=sec.section_key,
                title=sec.title,
                description=sec.description,
                order=sec.order,
                evidence_entries=[
                    EvidenceEntryRead(
                        evidence_id=e.evidence_id,
                        indicator=e.indicator,
                        value=e.value,
                        numeric_value=e.numeric_value,
                        unit=e.unit,
                        observed_at=e.observed_at,
                        data_source_id=e.data_source_id,
                        metadata_json=e.metadata_json,
                    )
                    for e in sec.evidence_entries
                ],
                summary_text=sec.summary_text,
            )
            for sec in scaffold.sections
        ],
        total_evidence_count=scaffold.total_evidence_count,
    )


@router.get(
    "/scaffold/{section_key}",
    response_model=ScaffoldSectionRead,
    summary="개별 섹션 초안 뼈대",
)
async def get_section_scaffold(
    project_id: uuid.UUID,
    section_key: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 섹션의 evidence 기반 초안 뼈대를 생성한다."""
    await _verify_project(db, project_id)

    scaffold = await generate_section_scaffold(db, project_id, section_key)
    if scaffold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"섹션을 찾을 수 없습니다: {section_key}",
        )

    return ScaffoldSectionRead(
        section_key=scaffold.section_key,
        title=scaffold.title,
        description=scaffold.description,
        order=scaffold.order,
        evidence_entries=[
            EvidenceEntryRead(
                evidence_id=e.evidence_id,
                indicator=e.indicator,
                value=e.value,
                numeric_value=e.numeric_value,
                unit=e.unit,
                observed_at=e.observed_at,
                data_source_id=e.data_source_id,
                metadata_json=e.metadata_json,
            )
            for e in scaffold.evidence_entries
        ],
        summary_text=scaffold.summary_text,
    )
