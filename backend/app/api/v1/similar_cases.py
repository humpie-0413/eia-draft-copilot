"""유사사례 API 엔드포인트."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import similar_case as crud
from app.crud.similar_case import _wkb_to_geojson
from app.crud.project import get_project
from app.db import get_db
from app.models.evidence import Evidence
from app.schemas.similar_case import (
    SimilarCaseCreate,
    SimilarCaseList,
    SimilarCaseMatchList,
    SimilarCaseRead,
    SimilarCaseUpdate,
)
from app.services.similarity import find_similar_cases

router = APIRouter(prefix="/similar-cases", tags=["similar-cases"])


def _to_read(case) -> SimilarCaseRead:
    """ORM SimilarCase → Pydantic SimilarCaseRead (geometry 변환 포함)."""
    return SimilarCaseRead(
        id=case.id,
        name=case.name,
        description=case.description,
        project_type=case.project_type,
        location=_wkb_to_geojson(case.location),
        area_sqm=case.area_sqm,
        completed_at=case.completed_at,
        summary=case.summary,
        key_findings=case.key_findings,
        evidence_categories=case.evidence_categories,
        source_url=case.source_url,
        metadata_json=case.metadata_json,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


# ── CRUD 엔드포인트 ──


@router.post("", response_model=SimilarCaseRead, status_code=status.HTTP_201_CREATED)
async def create_similar_case(
    data: SimilarCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """유사사례를 등록한다."""
    case = await crud.create_similar_case(db, data)
    return _to_read(case)


@router.get("", response_model=SimilarCaseList)
async def list_similar_cases(
    project_type: str | None = Query(None, description="사업 유형 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """유사사례 목록을 조회한다."""
    cases, total = await crud.list_similar_cases(
        db, project_type=project_type, skip=skip, limit=limit
    )
    return SimilarCaseList(items=[_to_read(c) for c in cases], total=total)


@router.get("/{case_id}", response_model=SimilarCaseRead)
async def get_similar_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """유사사례 상세 정보를 조회한다."""
    case = await crud.get_similar_case(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유사사례를 찾을 수 없습니다: {case_id}",
        )
    return _to_read(case)


@router.patch("/{case_id}", response_model=SimilarCaseRead)
async def update_similar_case(
    case_id: uuid.UUID,
    data: SimilarCaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """유사사례 정보를 수정한다."""
    case = await crud.get_similar_case(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유사사례를 찾을 수 없습니다: {case_id}",
        )
    updated = await crud.update_similar_case(db, case, data)
    return _to_read(updated)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_similar_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """유사사례를 삭제한다."""
    case = await crud.get_similar_case(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유사사례를 찾을 수 없습니다: {case_id}",
        )
    await crud.delete_similar_case(db, case)


# ── 프로젝트별 유사사례 매칭 엔드포인트 ──


@router.get(
    "/match/{project_id}",
    response_model=SimilarCaseMatchList,
)
async def match_similar_cases(
    project_id: uuid.UUID,
    top_k: int = Query(10, ge=1, le=50, description="반환할 최대 결과 수"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="최소 유사도 컷오프"),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트에 대한 유사사례를 유사도 순으로 검색한다.

    프로젝트의 사업 유형, 위치(geometry), 증거 데이터의 환경 분야를
    기반으로 유사도를 계산하여 순위를 매긴다.
    """
    # 프로젝트 존재 확인
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )

    # 프로젝트에 연결된 증거 데이터에서 환경 분야 목록 추출
    cat_result = await db.execute(
        select(Evidence.category)
        .where(Evidence.project_id == project_id)
        .distinct()
    )
    evidence_categories = {row[0] for row in cat_result.all()}

    # 프로젝트 면적 추정 (geometry가 있는 경우 ST_Area 활용)
    # 주: EPSG:4326 단위는 도(degree)이므로 근사적으로 m² 변환
    project_area_sqm = None
    if project.geometry is not None:
        from geoalchemy2 import func as geo_func

        area_result = await db.execute(
            select(
                geo_func.ST_Area(
                    geo_func.ST_Transform(
                        project.geometry, 3857
                    )
                )
            )
        )
        project_area_sqm = area_result.scalar_one_or_none()

    match_result = await find_similar_cases(
        db,
        project_id=project_id,
        evidence_categories=evidence_categories,
        project_area_sqm=project_area_sqm,
        top_k=top_k,
        min_score=min_score,
    )
    return match_result
