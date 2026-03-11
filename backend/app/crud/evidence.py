import uuid

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceFilter, EvidenceUpdate


def _point_to_wkb(geojson_point) -> str | None:
    """GeoJSON Point → WKB element (PostGIS 저장용)."""
    if geojson_point is None:
        return None
    shp = shapely_shape(geojson_point.model_dump())
    return from_shape(shp, srid=4326)


def _wkb_to_point(wkb_element) -> dict | None:
    """WKB element → GeoJSON Point dict."""
    if wkb_element is None:
        return None
    shp = to_shape(wkb_element)
    return shp.__geo_interface__


async def create_evidence(db: AsyncSession, data: EvidenceCreate) -> Evidence:
    evidence = Evidence(
        project_id=data.project_id,
        snapshot_id=data.snapshot_id,
        data_source_id=data.data_source_id,
        category=data.category.value,
        indicator=data.indicator,
        value=data.value,
        numeric_value=data.numeric_value,
        unit=data.unit,
        observed_at=data.observed_at,
        location=_point_to_wkb(data.location),
        metadata_json=data.metadata_json,
        screening_only=data.screening_only,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


async def create_evidences_bulk(
    db: AsyncSession, items: list[EvidenceCreate]
) -> list[Evidence]:
    """여러 증거를 한 번에 저장한다 (커넥터 정규화 결과 일괄 저장용)."""
    evidences = []
    for data in items:
        ev = Evidence(
            project_id=data.project_id,
            snapshot_id=data.snapshot_id,
            data_source_id=data.data_source_id,
            category=data.category.value,
            indicator=data.indicator,
            value=data.value,
            numeric_value=data.numeric_value,
            unit=data.unit,
            observed_at=data.observed_at,
            location=_point_to_wkb(data.location),
            metadata_json=data.metadata_json,
            screening_only=data.screening_only,
        )
        db.add(ev)
        evidences.append(ev)

    await db.commit()
    for ev in evidences:
        await db.refresh(ev)
    return evidences


async def get_evidence(db: AsyncSession, evidence_id: uuid.UUID) -> Evidence | None:
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    return result.scalar_one_or_none()


async def list_evidences(
    db: AsyncSession,
    project_id: uuid.UUID,
    filters: EvidenceFilter | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Evidence], int]:
    """프로젝트별 증거 목록 조회.

    filters.screening_only로 스크리닝 전용 데이터와 본 평가 데이터를 분리 조회한다.
    """
    query = select(Evidence).where(Evidence.project_id == project_id)
    count_query = (
        select(func.count())
        .select_from(Evidence)
        .where(Evidence.project_id == project_id)
    )

    if filters:
        if filters.category is not None:
            query = query.where(Evidence.category == filters.category.value)
            count_query = count_query.where(Evidence.category == filters.category.value)
        if filters.screening_only is not None:
            query = query.where(Evidence.screening_only == filters.screening_only)
            count_query = count_query.where(Evidence.screening_only == filters.screening_only)
        if filters.data_source_id is not None:
            query = query.where(Evidence.data_source_id == filters.data_source_id)
            count_query = count_query.where(Evidence.data_source_id == filters.data_source_id)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(Evidence.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def update_evidence(
    db: AsyncSession, evidence: Evidence, data: EvidenceUpdate
) -> Evidence:
    update_data = data.model_dump(exclude_unset=True)

    if "location" in update_data:
        update_data["location"] = _point_to_wkb(data.location)

    if "category" in update_data and update_data["category"] is not None:
        update_data["category"] = update_data["category"].value

    for field, value in update_data.items():
        setattr(evidence, field, value)

    await db.commit()
    await db.refresh(evidence)
    return evidence


async def delete_evidence(db: AsyncSession, evidence: Evidence) -> None:
    await db.delete(evidence)
    await db.commit()
