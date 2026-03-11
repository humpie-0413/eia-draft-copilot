import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import source_snapshot as crud
from app.db import get_db
from app.schemas.source_snapshot import (
    SourceSnapshotCreate,
    SourceSnapshotList,
    SourceSnapshotRead,
)

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.post("", response_model=SourceSnapshotRead, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    data: SourceSnapshotCreate,
    db: AsyncSession = Depends(get_db),
):
    """소스 스냅샷을 생성한다 (raw payload 저장)."""
    snapshot = await crud.create_snapshot(db, data)
    return snapshot


@router.get("", response_model=SourceSnapshotList)
async def list_snapshots(
    project_id: uuid.UUID = Query(..., description="프로젝트 ID"),
    data_source_id: uuid.UUID | None = Query(None, description="데이터 소스 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트별 스냅샷 목록을 조회한다."""
    snapshots, total = await crud.list_snapshots_by_project(
        db, project_id=project_id, skip=skip, limit=limit, data_source_id=data_source_id
    )
    return SourceSnapshotList(items=snapshots, total=total)


@router.get("/{snapshot_id}", response_model=SourceSnapshotRead)
async def get_snapshot(
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """스냅샷 상세 정보를 조회한다 (raw_payload 포함)."""
    snapshot = await crud.get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"스냅샷을 찾을 수 없습니다: {snapshot_id}",
        )
    return snapshot


@router.delete("/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snapshot(
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """스냅샷을 삭제한다."""
    snapshot = await crud.get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"스냅샷을 찾을 수 없습니다: {snapshot_id}",
        )
    await crud.delete_snapshot(db, snapshot)
