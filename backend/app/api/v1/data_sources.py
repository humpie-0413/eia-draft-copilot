import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import connector_registry
from app.crud import data_source as crud
from app.db import get_db
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceList,
    DataSourceRead,
    DataSourceUpdate,
)

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.post("", response_model=DataSourceRead, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """공공데이터 소스를 등록한다."""
    source = await crud.create_data_source(db, data)
    return source


@router.get("", response_model=DataSourceList)
async def list_data_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    enabled_only: bool = Query(False, description="활성화된 소스만 조회"),
    db: AsyncSession = Depends(get_db),
):
    """등록된 공공데이터 소스 목록을 조회한다."""
    sources, total = await crud.list_data_sources(
        db, skip=skip, limit=limit, enabled_only=enabled_only
    )
    return DataSourceList(items=sources, total=total)


@router.get("/connectors", tags=["data-sources"])
async def list_available_connectors():
    """사용 가능한 커넥터 목록을 반환한다."""
    return [
        {"connector_key": key, "display_name": conn.display_name}
        for key, conn in connector_registry.items()
    ]


@router.get("/{source_id}", response_model=DataSourceRead)
async def get_data_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """공공데이터 소스 상세 정보를 조회한다."""
    source = await crud.get_data_source(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데이터 소스를 찾을 수 없습니다: {source_id}",
        )
    return source


@router.patch("/{source_id}", response_model=DataSourceRead)
async def update_data_source(
    source_id: uuid.UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """공공데이터 소스 정보를 수정한다."""
    source = await crud.get_data_source(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데이터 소스를 찾을 수 없습니다: {source_id}",
        )
    return await crud.update_data_source(db, source, data)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """공공데이터 소스를 삭제한다."""
    source = await crud.get_data_source(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데이터 소스를 찾을 수 없습니다: {source_id}",
        )
    await crud.delete_data_source(db, source)
