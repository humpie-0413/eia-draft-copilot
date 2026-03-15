"""공간 분석 및 도면 생성 API.

/api/v1/projects/{project_id}/spatial/buffer — 버퍼 GeoJSON
/api/v1/projects/{project_id}/spatial/overlay — 버퍼 내 규제 항목
/api/v1/projects/{project_id}/maps/{map_type} — 도면 PNG
/api/v1/projects/{project_id}/maps — 사용 가능한 도면 목록
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from geoalchemy2.shape import to_shape
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.project import Project
from app.services.spatial_analysis import (
    BufferResult,
    OverlayItem,
    OverlayResult,
    get_overlay_items,
    get_project_buffer,
)
from app.services.map_renderer import (
    MAP_TYPES,
    MapRenderContext,
    render_map,
    save_map,
)

router = APIRouter(tags=["spatial"])


# ── 응답 스키마 ──

class BufferResponse(BaseModel):
    """버퍼 분석 응답."""
    project_id: str
    radius_m: float
    buffer_geojson: dict
    centroid: list[float]  # [lat, lon]
    area_km2: float


class OverlayItemResponse(BaseModel):
    """오버레이 항목 응답."""
    name: str
    item_type: str
    category: str
    distance_m: float
    lat: float
    lon: float
    metadata: dict


class OverlayResponse(BaseModel):
    """중첩 분석 응답."""
    project_id: str
    radius_m: float
    items: list[OverlayItemResponse]
    total_count: int


class MapTypeResponse(BaseModel):
    """도면 유형 응답."""
    map_type: str
    title: str


class MapListResponse(BaseModel):
    """도면 목록 응답."""
    maps: list[MapTypeResponse]


# ── 버퍼 분석 ──

@router.get(
    "/projects/{project_id}/spatial/buffer",
    response_model=BufferResponse,
)
async def get_buffer(
    project_id: uuid.UUID,
    radius: float = Query(default=1000.0, ge=100, le=50000, description="버퍼 반경 (m)"),
    db: AsyncSession = Depends(get_db),
):
    """사업 경계 기준 버퍼 GeoJSON을 반환한다."""
    result = await get_project_buffer(db, project_id, radius)
    if result is None:
        raise HTTPException(status_code=404, detail="프로젝트 또는 geometry를 찾을 수 없습니다.")

    return BufferResponse(
        project_id=result.project_id,
        radius_m=result.radius_m,
        buffer_geojson=result.buffer_geojson,
        centroid=list(result.centroid),
        area_km2=result.area_km2,
    )


# ── 중첩 분석 ──

@router.get(
    "/projects/{project_id}/spatial/overlay",
    response_model=OverlayResponse,
)
async def get_overlay(
    project_id: uuid.UUID,
    radius: float = Query(default=1000.0, ge=100, le=50000, description="탐색 반경 (m)"),
    db: AsyncSession = Depends(get_db),
):
    """버퍼 내 규제 항목(측정소, 문화재 등) 목록을 반환한다."""
    result = await get_overlay_items(db, project_id, radius)

    return OverlayResponse(
        project_id=result.project_id,
        radius_m=result.radius_m,
        items=[
            OverlayItemResponse(
                name=item.name,
                item_type=item.item_type,
                category=item.category,
                distance_m=item.distance_m,
                lat=item.lat,
                lon=item.lon,
                metadata=item.metadata,
            )
            for item in result.items
        ],
        total_count=result.total_count,
    )


# ── 도면 목록 ──

@router.get(
    "/projects/{project_id}/maps",
    response_model=MapListResponse,
)
async def list_maps(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """사용 가능한 도면 유형 목록을 반환한다."""
    # 프로젝트 존재 확인
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    return MapListResponse(
        maps=[
            MapTypeResponse(map_type=k, title=v)
            for k, v in MAP_TYPES.items()
        ]
    )


# ── 도면 렌더링 ──

@router.get(
    "/projects/{project_id}/maps/{map_type}",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_map(
    project_id: uuid.UUID,
    map_type: str,
    save: bool = Query(default=False, description="파일로 저장 여부"),
    db: AsyncSession = Depends(get_db),
):
    """지정된 도면 유형의 PNG 이미지를 반환한다.

    map_type: location, land_use, monitoring_stations, noise_contour, air_dispersion
    """
    if map_type not in MAP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도면 유형: {map_type}. "
                   f"가능한 유형: {', '.join(MAP_TYPES.keys())}",
        )

    # 프로젝트 조회
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    # 렌더링 컨텍스트 구성
    ctx = await _build_map_context(db, project, map_type)

    # 도면 렌더링
    png_bytes = render_map(map_type, ctx)
    if png_bytes is None:
        raise HTTPException(status_code=422, detail="도면 렌더링에 실패했습니다. geometry가 필요합니다.")

    # 파일 저장 (선택)
    if save:
        save_map(map_type, ctx)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename={project_id}_{map_type}.png",
        },
    )


async def _build_map_context(
    db: AsyncSession,
    project: Project,
    map_type: str,
) -> MapRenderContext:
    """도면 렌더링에 필요한 컨텍스트를 구성한다."""
    ctx = MapRenderContext(
        project_id=str(project.id),
        project_name=project.name,
        geometry_wkb=project.geometry,
    )

    if project.geometry:
        geom = to_shape(project.geometry)
        ctx.centroid = (round(geom.centroid.y, 6), round(geom.centroid.x, 6))

    # 오버레이 항목 (위치도, 측정소 분포도에서 사용)
    if map_type in ("location", "monitoring_stations"):
        overlay = await get_overlay_items(db, project.id, radius_m=5000.0)
        ctx.overlay_items = overlay.items

    # 토지이용 데이터
    if map_type == "land_use":
        ctx.land_use_data = await _get_land_use_data(db, project.id)

    # 예측 결과 (소음/대기 등고선도)
    if map_type in ("noise_contour", "air_dispersion"):
        ctx.prediction_result = await _get_prediction_result(
            db, project.id, map_type,
        )

    return ctx


async def _get_land_use_data(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """토지이용 증거 데이터를 조회한다."""
    from app.models.evidence import Evidence

    stmt = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .where(Evidence.category == "land_use")
    )
    result = await db.execute(stmt)
    evidences = result.scalars().all()

    land_use_items = []
    for ev in evidences:
        meta = ev.metadata_json or {}
        item = {
            "zone_name": meta.get("zone_name", ev.value),
            "indicator": ev.indicator,
        }
        # location이 있으면 좌표 추가
        if ev.location:
            try:
                pt = to_shape(ev.location)
                item["lat"] = pt.y
                item["lon"] = pt.x
            except Exception:
                pass
        land_use_items.append(item)

    return land_use_items


async def _get_prediction_result(
    db: AsyncSession,
    project_id: uuid.UUID,
    map_type: str,
) -> object | None:
    """예측 결과를 조회한다."""
    from app.services.draft_scaffold import generate_draft_scaffold

    try:
        scaffold = await generate_draft_scaffold(db, project_id)
    except Exception:
        return None

    section_key = "noise_vibration" if map_type == "noise_contour" else "air_quality"

    for section in scaffold.sections:
        if section.section_key == section_key and section.prediction_result:
            return section.prediction_result

    return None
