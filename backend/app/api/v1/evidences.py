import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import evidence as crud
from app.crud.evidence import _wkb_to_point
from app.db import get_db
from app.schemas.evidence import (
    EvidenceCategory,
    EvidenceCreate,
    EvidenceFilter,
    EvidenceList,
    EvidenceRead,
    EvidenceUpdate,
)

router = APIRouter(prefix="/evidences", tags=["evidences"])


def _to_read(ev) -> EvidenceRead:
    """ORM Evidence → Pydantic EvidenceRead (location 변환 포함)."""
    return EvidenceRead(
        id=ev.id,
        project_id=ev.project_id,
        snapshot_id=ev.snapshot_id,
        data_source_id=ev.data_source_id,
        category=ev.category,
        indicator=ev.indicator,
        value=ev.value,
        numeric_value=ev.numeric_value,
        unit=ev.unit,
        observed_at=ev.observed_at,
        location=_wkb_to_point(ev.location),
        metadata_json=ev.metadata_json,
        screening_only=ev.screening_only,
        created_at=ev.created_at,
    )


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    data: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
):
    """증거 데이터를 생성한다."""
    evidence = await crud.create_evidence(db, data)
    return _to_read(evidence)


@router.get("", response_model=EvidenceList)
async def list_evidences(
    project_id: uuid.UUID = Query(..., description="프로젝트 ID"),
    category: EvidenceCategory | None = Query(None, description="환경 분야 필터"),
    screening_only: bool | None = Query(None, description="스크리닝 전용 데이터 필터"),
    data_source_id: uuid.UUID | None = Query(None, description="데이터 소스 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트별 증거 목록을 조회한다.

    screening_only 파라미터:
    - None: 전체 조회
    - True: 스크리닝 전용 데이터만
    - False: 본 평가 데이터만
    """
    filters = EvidenceFilter(
        category=category,
        screening_only=screening_only,
        data_source_id=data_source_id,
    )
    evidences, total = await crud.list_evidences(
        db, project_id=project_id, filters=filters, skip=skip, limit=limit
    )
    return EvidenceList(items=[_to_read(e) for e in evidences], total=total)


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """증거 데이터 상세 정보를 조회한다."""
    evidence = await crud.get_evidence(db, evidence_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"증거를 찾을 수 없습니다: {evidence_id}",
        )
    return _to_read(evidence)


@router.patch("/{evidence_id}", response_model=EvidenceRead)
async def update_evidence(
    evidence_id: uuid.UUID,
    data: EvidenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """증거 데이터를 수정한다."""
    evidence = await crud.get_evidence(db, evidence_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"증거를 찾을 수 없습니다: {evidence_id}",
        )
    updated = await crud.update_evidence(db, evidence, data)
    return _to_read(updated)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """증거 데이터를 삭제한다."""
    evidence = await crud.get_evidence(db, evidence_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"증거를 찾을 수 없습니다: {evidence_id}",
        )
    await crud.delete_evidence(db, evidence)
