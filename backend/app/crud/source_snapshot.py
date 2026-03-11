import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_snapshot import SourceSnapshot
from app.schemas.source_snapshot import SourceSnapshotCreate


async def create_snapshot(db: AsyncSession, data: SourceSnapshotCreate) -> SourceSnapshot:
    """스냅샷을 생성하고 raw_payload를 JSONB로 저장한다."""
    snapshot = SourceSnapshot(
        data_source_id=data.data_source_id,
        project_id=data.project_id,
        query_params=data.query_params,
        raw_payload=data.raw_payload,
        status=data.status.value if data.status else "success",
        error_message=data.error_message,
    )
    if data.fetched_at:
        snapshot.fetched_at = data.fetched_at

    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_snapshot(db: AsyncSession, snapshot_id: uuid.UUID) -> SourceSnapshot | None:
    result = await db.execute(
        select(SourceSnapshot).where(SourceSnapshot.id == snapshot_id)
    )
    return result.scalar_one_or_none()


async def list_snapshots_by_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    data_source_id: uuid.UUID | None = None,
) -> tuple[list[SourceSnapshot], int]:
    """프로젝트별 스냅샷 목록을 조회한다."""
    query = select(SourceSnapshot).where(SourceSnapshot.project_id == project_id)
    count_query = (
        select(func.count())
        .select_from(SourceSnapshot)
        .where(SourceSnapshot.project_id == project_id)
    )

    if data_source_id:
        query = query.where(SourceSnapshot.data_source_id == data_source_id)
        count_query = count_query.where(SourceSnapshot.data_source_id == data_source_id)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(SourceSnapshot.fetched_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def delete_snapshot(db: AsyncSession, snapshot: SourceSnapshot) -> None:
    await db.delete(snapshot)
    await db.commit()
