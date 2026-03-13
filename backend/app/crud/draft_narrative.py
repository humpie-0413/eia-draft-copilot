"""LLM 보강 서술문 CRUD 함수."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.draft_narrative import DraftNarrative


async def get_narrative(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
) -> DraftNarrative | None:
    """프로젝트+섹션에 대한 보강 서술문을 조회한다."""
    result = await db.execute(
        select(DraftNarrative).where(
            (DraftNarrative.project_id == project_id)
            & (DraftNarrative.section_key == section_key)
        )
    )
    return result.scalar_one_or_none()


async def get_all_narratives(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, DraftNarrative]:
    """프로젝트의 모든 보강 서술문을 섹션키 딕셔너리로 반환한다."""
    result = await db.execute(
        select(DraftNarrative).where(DraftNarrative.project_id == project_id)
    )
    return {row.section_key: row for row in result.scalars().all()}


async def upsert_narrative(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
    narrative_text: str,
    adapter_used: str,
) -> DraftNarrative:
    """보강 서술문을 저장하거나 업데이트한다 (upsert)."""
    existing = await get_narrative(db, project_id, section_key)
    if existing:
        existing.narrative_text = narrative_text
        existing.adapter_used = adapter_used
        await db.flush()
        return existing

    row = DraftNarrative(
        project_id=project_id,
        section_key=section_key,
        narrative_text=narrative_text,
        adapter_used=adapter_used,
    )
    db.add(row)
    await db.flush()
    return row
