"""유사도 계산 서비스.

프로젝트와 유사사례 간 유사도를 사업 유형, 위치, 규모, 환경 분야
네 가지 축으로 계산하여 종합 점수를 산출한다.
"""

import math
import uuid

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.similar_case import list_all_similar_cases, _wkb_to_geojson
from app.crud.project import get_project
from app.models.project import Project
from app.models.similar_case import SimilarCase
from app.schemas.similar_case import (
    SimilarCaseMatchList,
    SimilarCaseMatchResult,
    SimilarCaseRead,
)

# ── 사업 유형 그룹 ──
# 유사한 유형끼리 그룹으로 묶어 부분 점수를 부여
_TYPE_GROUPS: dict[str, str] = {
    "road": "transport",
    "railway": "transport",
    "airport": "transport",
    "port": "transport",
    "power_plant": "energy",
    "industrial": "development",
    "housing": "development",
    "reclamation": "land",
    "dam": "water",
    "other": "other",
}

# ── 가중치 (합 = 1.0) ──
WEIGHT_TYPE = 0.35
WEIGHT_LOCATION = 0.25
WEIGHT_SCALE = 0.20
WEIGHT_CATEGORY = 0.20

# ── 위치 유사도 계산 시 기준 거리 (km) ──
# 이 거리 이하이면 높은 점수, 이상이면 점수가 감쇠
DISTANCE_HALF_SCORE_KM = 50.0  # 50km에서 유사도 0.5


def _compute_type_score(project_type: str | None, case_type: str) -> float:
    """사업 유형 유사도 계산.

    - 동일 유형: 1.0
    - 같은 그룹: 0.5
    - 다른 그룹: 0.0
    """
    if project_type is None:
        return 0.0
    if project_type == case_type:
        return 1.0
    project_group = _TYPE_GROUPS.get(project_type, "other")
    case_group = _TYPE_GROUPS.get(case_type, "other")
    if project_group == case_group and project_group != "other":
        return 0.5
    return 0.0


def _compute_location_score(
    project_geom_wkb, case_geom_wkb
) -> float:
    """위치 유사도 계산.

    두 지오메트리의 centroid 간 대권 거리(haversine)를 사용한다.
    지오메트리가 없으면 0.0을 반환한다.
    """
    if project_geom_wkb is None or case_geom_wkb is None:
        return 0.0

    p_shape = to_shape(project_geom_wkb)
    c_shape = to_shape(case_geom_wkb)

    # centroid 좌표 (lon, lat)
    p_centroid = p_shape.centroid
    c_centroid = c_shape.centroid

    dist_km = _haversine_km(
        p_centroid.y, p_centroid.x, c_centroid.y, c_centroid.x
    )

    # 지수 감쇠: 거리가 0이면 1.0, DISTANCE_HALF_SCORE_KM이면 0.5
    decay = math.log(2) / DISTANCE_HALF_SCORE_KM
    return math.exp(-decay * dist_km)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 대권 거리 (km)."""
    R = 6371.0  # 지구 반지름 (km)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_scale_score(
    project_area: float | None, case_area: float | None
) -> float:
    """규모(면적) 유사도 계산.

    두 면적의 비율로 계산한다. 면적이 없으면 0.0.
    비율 = min(a, b) / max(a, b) → 동일하면 1.0, 차이 클수록 0에 수렴.
    """
    if not project_area or not case_area:
        return 0.0
    if project_area <= 0 or case_area <= 0:
        return 0.0
    ratio = min(project_area, case_area) / max(project_area, case_area)
    return ratio


def _compute_category_score(
    project_categories: set[str], case_categories: list[str] | None
) -> float:
    """환경 분야 유사도 계산.

    프로젝트의 증거 분야와 유사사례의 환경 분야 간 Jaccard 유사도.
    어느 한쪽이 비어 있으면 0.0.
    """
    if not project_categories or not case_categories:
        return 0.0
    case_set = set(case_categories)
    intersection = project_categories & case_set
    union = project_categories | case_set
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _case_to_read(case: SimilarCase) -> SimilarCaseRead:
    """ORM SimilarCase → Pydantic SimilarCaseRead."""
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


async def find_similar_cases(
    db: AsyncSession,
    project_id: uuid.UUID,
    evidence_categories: set[str] | None = None,
    project_area_sqm: float | None = None,
    top_k: int = 10,
    min_score: float = 0.0,
) -> SimilarCaseMatchList:
    """프로젝트에 대한 유사사례를 검색하여 유사도 순으로 반환한다.

    Args:
        db: DB 세션
        project_id: 대상 프로젝트 ID
        evidence_categories: 프로젝트의 증거 분야 집합 (외부에서 전달)
        project_area_sqm: 프로젝트 사업 면적 (외부에서 전달, 없으면 스킵)
        top_k: 반환할 최대 결과 수
        min_score: 최소 유사도 컷오프

    Returns:
        SimilarCaseMatchList
    """
    project = await get_project(db, project_id)
    if project is None:
        return SimilarCaseMatchList(
            project_id=project_id, matches=[], total=0
        )

    all_cases = await list_all_similar_cases(db)
    project_cats = evidence_categories or set()

    results: list[SimilarCaseMatchResult] = []

    for case in all_cases:
        type_score = _compute_type_score(project.project_type, case.project_type)
        location_score = _compute_location_score(
            project.geometry, case.location
        )
        scale_score = _compute_scale_score(project_area_sqm, case.area_sqm)
        category_score = _compute_category_score(
            project_cats, case.evidence_categories
        )

        overall = (
            WEIGHT_TYPE * type_score
            + WEIGHT_LOCATION * location_score
            + WEIGHT_SCALE * scale_score
            + WEIGHT_CATEGORY * category_score
        )

        if overall < min_score:
            continue

        results.append(
            SimilarCaseMatchResult(
                similar_case=_case_to_read(case),
                overall_score=round(overall, 4),
                type_score=round(type_score, 4),
                location_score=round(location_score, 4),
                scale_score=round(scale_score, 4),
                category_score=round(category_score, 4),
            )
        )

    # 종합 점수 기준 내림차순 정렬
    results.sort(key=lambda r: r.overall_score, reverse=True)
    results = results[:top_k]

    return SimilarCaseMatchList(
        project_id=project_id,
        matches=results,
        total=len(results),
    )
