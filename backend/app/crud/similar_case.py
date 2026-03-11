"""유사사례 CRUD 함수."""

import uuid

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.similar_case import SimilarCase
from app.schemas.similar_case import SimilarCaseCreate, SimilarCaseUpdate


def _geojson_to_wkb(geojson_geom) -> str | None:
    """GeoJSON geometry → WKB element (PostGIS 저장용)."""
    if geojson_geom is None:
        return None
    geom_dict = geojson_geom.model_dump()
    shp = shapely_shape(geom_dict)
    return from_shape(shp, srid=4326)


def _wkb_to_geojson(wkb_element) -> dict | None:
    """WKB element → GeoJSON dict."""
    if wkb_element is None:
        return None
    shp = to_shape(wkb_element)
    return shp.__geo_interface__


async def create_similar_case(
    db: AsyncSession, data: SimilarCaseCreate
) -> SimilarCase:
    case = SimilarCase(
        name=data.name,
        description=data.description,
        project_type=data.project_type,
        location=_geojson_to_wkb(data.location),
        area_sqm=data.area_sqm,
        completed_at=data.completed_at,
        summary=data.summary,
        key_findings=data.key_findings,
        evidence_categories=(
            [c.value if hasattr(c, "value") else c for c in data.evidence_categories]
            if data.evidence_categories
            else None
        ),
        source_url=data.source_url,
        metadata_json=data.metadata_json,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


async def get_similar_case(
    db: AsyncSession, case_id: uuid.UUID
) -> SimilarCase | None:
    result = await db.execute(
        select(SimilarCase).where(SimilarCase.id == case_id)
    )
    return result.scalar_one_or_none()


async def list_similar_cases(
    db: AsyncSession,
    project_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SimilarCase], int]:
    """유사사례 목록 조회. project_type으로 필터링 가능."""
    query = select(SimilarCase)
    count_query = select(func.count()).select_from(SimilarCase)

    if project_type:
        query = query.where(SimilarCase.project_type == project_type)
        count_query = count_query.where(SimilarCase.project_type == project_type)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(SimilarCase.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def list_all_similar_cases(db: AsyncSession) -> list[SimilarCase]:
    """유사도 계산을 위해 전체 유사사례를 조회한다."""
    result = await db.execute(
        select(SimilarCase).order_by(SimilarCase.created_at.desc())
    )
    return list(result.scalars().all())


async def update_similar_case(
    db: AsyncSession, case: SimilarCase, data: SimilarCaseUpdate
) -> SimilarCase:
    update_data = data.model_dump(exclude_unset=True)

    if "location" in update_data:
        update_data["location"] = _geojson_to_wkb(data.location)

    if "evidence_categories" in update_data and update_data["evidence_categories"]:
        update_data["evidence_categories"] = [
            c.value if hasattr(c, "value") else c
            for c in update_data["evidence_categories"]
        ]

    for field, value in update_data.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)
    return case


async def delete_similar_case(db: AsyncSession, case: SimilarCase) -> None:
    await db.delete(case)
    await db.commit()
