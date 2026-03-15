"""공간 분석 서비스 — PostGIS 기반 버퍼 분석 및 규제 항목 중첩 탐색.

사업 경계 geometry를 기반으로:
1. ST_Buffer 대신 shapely + pyproj로 버퍼 생성 (EPSG:4326 → 5179 → buffer → 4326)
2. 버퍼 내 evidence 좌표 탐색
3. 규제 항목(문화재, 측정소 등) 거리 계산
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from geoalchemy2.shape import to_shape
from pyproj import Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.models.project import Project


# ── 좌표 변환기 (WGS84 ↔ TM(Korea Central)) ──

_to_5179 = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
_to_4326 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)


@dataclass
class BufferResult:
    """버퍼 분석 결과."""

    project_id: str
    radius_m: float
    buffer_geojson: dict          # GeoJSON Polygon
    centroid: tuple[float, float]  # (lat, lon)
    area_km2: float                # 버퍼 면적 (km²)


@dataclass
class OverlayItem:
    """버퍼 내 탐지된 항목."""

    name: str
    item_type: str           # "측정소", "문화재", "증거" 등
    category: str            # evidence category
    distance_m: float        # 사업 경계 중심점으로부터 거리
    lat: float
    lon: float
    metadata: dict = field(default_factory=dict)


@dataclass
class OverlayResult:
    """중첩 분석 결과."""

    project_id: str
    radius_m: float
    items: list[OverlayItem]
    total_count: int


def _project_to_5179(geom):
    """shapely geometry를 EPSG:4326 → EPSG:5179로 변환."""
    return transform(_to_5179.transform, geom)


def _project_to_4326(geom):
    """shapely geometry를 EPSG:5179 → EPSG:4326로 변환."""
    return transform(_to_4326.transform, geom)


def compute_buffer(geometry_wkb, radius_m: float) -> BufferResult | None:
    """사업 경계 geometry에 대해 미터 단위 버퍼를 생성한다.

    EPSG:4326 → EPSG:5179(TM) 변환 후 미터 단위 버퍼를 생성하고,
    다시 EPSG:4326으로 역변환하여 GeoJSON으로 반환한다.

    Args:
        geometry_wkb: PostGIS WKB geometry
        radius_m: 버퍼 반경 (m)

    Returns:
        BufferResult 또는 None
    """
    if geometry_wkb is None:
        return None

    try:
        geom_4326 = to_shape(geometry_wkb)
    except Exception:
        return None

    centroid_4326 = geom_4326.centroid
    lat, lon = centroid_4326.y, centroid_4326.x

    # TM 좌표계로 변환 → 미터 단위 버퍼 → WGS84로 역변환
    geom_5179 = _project_to_5179(geom_4326)
    buffer_5179 = geom_5179.buffer(radius_m)
    buffer_4326 = _project_to_4326(buffer_5179)

    # 면적 계산 (5179 좌표계에서, km² 단위)
    area_km2 = buffer_5179.area / 1e6

    return BufferResult(
        project_id="",
        radius_m=radius_m,
        buffer_geojson=mapping(buffer_4326),
        centroid=(round(lat, 6), round(lon, 6)),
        area_km2=round(area_km2, 3),
    )


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 거리를 미터 단위로 계산 (Haversine)."""
    R = 6371000  # 지구 반경 (m)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_project_buffer(
    db: AsyncSession,
    project_id: uuid.UUID,
    radius_m: float = 1000.0,
) -> BufferResult | None:
    """프로젝트 geometry 기반 버퍼를 생성한다."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None or project.geometry is None:
        return None

    buf = compute_buffer(project.geometry, radius_m)
    if buf:
        buf.project_id = str(project_id)
    return buf


async def get_overlay_items(
    db: AsyncSession,
    project_id: uuid.UUID,
    radius_m: float = 1000.0,
) -> OverlayResult:
    """버퍼 내 증거 데이터(측정소, 문화재 등)를 탐색한다.

    evidence 테이블에서 location이 있는 항목을 조회하고,
    사업 경계 중심점으로부터의 거리를 계산하여 버퍼 반경 내 항목을 반환한다.
    """
    # 프로젝트 geometry 중심점 확인
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None or project.geometry is None:
        return OverlayResult(
            project_id=str(project_id),
            radius_m=radius_m,
            items=[],
            total_count=0,
        )

    try:
        geom = to_shape(project.geometry)
        center_lat, center_lon = geom.centroid.y, geom.centroid.x
    except Exception:
        return OverlayResult(
            project_id=str(project_id),
            radius_m=radius_m,
            items=[],
            total_count=0,
        )

    # location이 있는 evidence 조회
    stmt = (
        select(Evidence)
        .where(Evidence.project_id == project_id)
        .where(Evidence.location.isnot(None))
    )
    ev_result = await db.execute(stmt)
    evidences = ev_result.scalars().all()

    items: list[OverlayItem] = []
    for ev in evidences:
        try:
            pt = to_shape(ev.location)
            ev_lat, ev_lon = pt.y, pt.x
        except Exception:
            continue

        dist = _haversine_distance(center_lat, center_lon, ev_lat, ev_lon)
        if dist > radius_m:
            continue

        # 측정소명/문화재명 추출
        name = ""
        item_type = "증거"
        meta = ev.metadata_json or {}

        if ev.category == "air_quality":
            name = meta.get("station_name", ev.indicator)
            item_type = "대기측정소"
        elif ev.category == "water_quality":
            name = meta.get("station_name", meta.get("site_name", ev.indicator))
            item_type = "수질측정소"
        elif ev.category == "noise_vibration":
            name = meta.get("station_name", ev.indicator)
            item_type = "소음측정소"
        elif ev.category == "cultural_heritage":
            name = meta.get("name", meta.get("ccba_nm", ev.indicator))
            item_type = "문화재"
        elif ev.category == "ecology":
            name = meta.get("species", ev.indicator)
            item_type = "생태조사지점"
        elif ev.category == "soil":
            name = meta.get("station_name", ev.indicator)
            item_type = "토양측정소"
        else:
            name = ev.indicator
            item_type = "기타"

        items.append(OverlayItem(
            name=name,
            item_type=item_type,
            category=ev.category,
            distance_m=round(dist, 1),
            lat=round(ev_lat, 6),
            lon=round(ev_lon, 6),
            metadata={
                "indicator": ev.indicator,
                "value": ev.value,
                "unit": ev.unit,
            },
        ))

    # 거리순 정렬
    items.sort(key=lambda x: x.distance_m)

    return OverlayResult(
        project_id=str(project_id),
        radius_m=radius_m,
        items=items,
        total_count=len(items),
    )
