"""국가유산청 문화재 커넥터.

국가유산청 Open API를 통해 프로젝트 인근 문화재 정보를 조회한다.
- 목록 조회: https://www.khs.go.kr/cha/SearchKindOpenapiList.do
- 상세 조회: https://www.khs.go.kr/cha/SearchKindOpenapiDt.do
- 시도코드 기반 조회 후 프로젝트 중심점과의 거리 필터링 (반경 1km)
- API 키 불필요 (Open API)
- 응답: XML
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx

from app.config import settings
from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate

logger = logging.getLogger(__name__)

# 국가유산청 Open API 엔드포인트
CHA_LIST_URL = "https://www.khs.go.kr/cha/SearchKindOpenapiList.do"
CHA_DETAIL_URL = "https://www.khs.go.kr/cha/SearchKindOpenapiDt.do"

# 시도코드 매핑 (프로젝트 좌표 → 시도코드)
SIDO_CODES: dict[str, str] = {
    "서울": "11", "부산": "21", "대구": "22", "인천": "23",
    "광주": "24", "대전": "25", "울산": "26", "세종": "29",
    "경기": "31", "강원": "32", "충북": "33", "충남": "34",
    "전북": "35", "전남": "36", "경북": "37", "경남": "38",
    "제주": "39",
}

# 위도/경도 범위 → 시도 코드 대략 매핑 (중심 좌표 기반)
_COORD_SIDO_MAP: list[tuple[float, float, float, float, str]] = [
    # (min_lat, max_lat, min_lng, max_lng, sido_code)
    (37.4, 37.7, 126.7, 127.2, "11"),  # 서울
    (34.9, 35.3, 128.8, 129.3, "21"),  # 부산
    (35.7, 36.0, 128.4, 128.8, "22"),  # 대구
    (37.3, 37.6, 126.3, 126.8, "23"),  # 인천
    (35.0, 35.3, 126.7, 127.0, "24"),  # 광주
    (36.2, 36.5, 127.2, 127.6, "25"),  # 대전
    (35.4, 35.7, 129.0, 129.5, "26"),  # 울산
    (36.4, 36.7, 126.8, 127.1, "29"),  # 세종
    (37.0, 37.9, 126.4, 127.8, "31"),  # 경기
    (37.0, 38.6, 127.5, 129.4, "32"),  # 강원
    (36.2, 37.1, 127.2, 128.2, "33"),  # 충북
    (35.9, 36.9, 125.9, 127.3, "34"),  # 충남
    (35.3, 36.1, 126.5, 127.9, "35"),  # 전북
    (34.0, 35.5, 126.0, 127.5, "36"),  # 전남
    (35.5, 37.1, 128.2, 130.0, "37"),  # 경북
    (34.6, 35.7, 127.5, 129.0, "38"),  # 경남
    (33.0, 34.0, 126.0, 127.0, "39"),  # 제주
]

# 반경 필터 (미터)
MAX_DISTANCE_M = 1000


def _coord_to_sido(lat: float, lng: float) -> str:
    """좌표를 시도코드로 변환한다. 가장 가까운 영역을 선택."""
    for min_lat, max_lat, min_lng, max_lng, code in _COORD_SIDO_MAP:
        if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
            return code
    return "11"  # 기본값: 서울


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리를 미터 단위로 계산한다 (Haversine 공식)."""
    R = 6371000  # 지구 반경 (m)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class CulturalHeritageConnector(BaseConnector):
    """국가유산청 문화재 커넥터."""

    connector_key = "cultural_heritage"
    display_name = "국가유산청 문화재 조회"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """국가유산청 Open API를 호출하여 문화재 목록을 반환한다.

        params:
            lng: 경도 (프로젝트 geometry 중심점)
            lat: 위도 (프로젝트 geometry 중심점)
            ccba_ctcd: 시도코드 (선택, 미입력 시 좌표에서 추론)
            page_index: 페이지 인덱스 (기본 1)
            page_unit: 페이지당 건수 (기본 100)

        Returns:
            파싱된 문화재 목록 딕셔너리
        """
        lat = params.get("lat")
        lng = params.get("lng")
        if lat is None or lng is None:
            raise ValueError("lat(위도)와 lng(경도) 파라미터가 필요합니다.")

        lat = float(lat)
        lng = float(lng)

        # 시도코드 결정
        ccba_ctcd = params.get("ccba_ctcd") or _coord_to_sido(lat, lng)

        query_params = {
            "ccbaCtcd": ccba_ctcd,
            "pageIndex": str(params.get("page_index", 1)),
            "pageUnit": str(params.get("page_unit", 100)),
        }

        logger.info(
            "국가유산청 API 호출: 시도코드=%s, 좌표=(%s, %s)",
            ccba_ctcd, lat, lng,
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(CHA_LIST_URL, params=query_params)
            response.raise_for_status()
            xml_text = response.text

        # XML 파싱
        items = self._parse_list_xml(xml_text)

        # 좌표 기반 거리 필터링
        filtered_items = []
        for item in items:
            item_lat = item.get("latitude")
            item_lng = item.get("longitude")
            if item_lat is not None and item_lng is not None:
                try:
                    dist = _haversine_distance(
                        lat, lng, float(item_lat), float(item_lng)
                    )
                    item["distance_m"] = round(dist)
                    if dist <= MAX_DISTANCE_M:
                        filtered_items.append(item)
                except (ValueError, TypeError):
                    pass

        logger.info(
            "국가유산청 API 응답: 전체 %d건, 반경 %dm 이내 %d건",
            len(items), MAX_DISTANCE_M, len(filtered_items),
        )

        return {
            "total_count": len(items),
            "filtered_count": len(filtered_items),
            "center_lat": lat,
            "center_lng": lng,
            "sido_code": ccba_ctcd,
            "radius_m": MAX_DISTANCE_M,
            "items": filtered_items,
        }

    @staticmethod
    def _parse_list_xml(xml_text: str) -> list[dict[str, Any]]:
        """국가유산청 목록 XML 응답을 파싱한다."""
        items: list[dict[str, Any]] = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            logger.warning("국가유산청 XML 파싱 실패: %s", e)
            return items

        for item_el in root.findall(".//item"):
            item: dict[str, Any] = {}
            for child in item_el:
                tag = child.tag
                text = (child.text or "").strip()
                item[tag] = text
            items.append(item)

        return items

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """국가유산청 응답을 EvidenceCreate 목록으로 변환한다."""
        evidences: list[EvidenceCreate] = []

        items = raw_payload.get("items", [])

        if not items:
            logger.warning("국가유산청 응답에 인근 문화재가 없습니다.")
            return evidences

        now = datetime.now(tz=timezone.utc)

        for item in items:
            name = item.get("ccbaMnm1", "") or item.get("ccbaMnm2", "")
            kind = item.get("ccbaKdcd", "")
            kind_name = self._kind_code_to_name(kind)
            distance = item.get("distance_m", "")
            addr = item.get("ccbaLcad", "")

            if not name:
                continue

            # 문화재명 증거
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.CULTURAL_HERITAGE,
                    indicator="문화재명",
                    value=name,
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "kind": kind_name,
                        "distance_m": distance,
                        "address": addr,
                        "ccba_asno": item.get("ccbaAsno", ""),
                        "ccba_ctcd": item.get("ccbaCtcdNm", ""),
                    },
                )
            )

            # 종별 증거
            if kind_name:
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.CULTURAL_HERITAGE,
                        indicator="종별",
                        value=kind_name,
                        unit=None,
                        observed_at=now,
                        screening_only=screening_only,
                        metadata_json={
                            "heritage_name": name,
                            "kind_code": kind,
                        },
                    )
                )

            # 거리 증거
            if distance != "":
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.CULTURAL_HERITAGE,
                        indicator="이격거리",
                        value=str(distance),
                        numeric_value=float(distance) if distance else None,
                        unit="m",
                        observed_at=now,
                        screening_only=screening_only,
                        metadata_json={
                            "heritage_name": name,
                            "kind": kind_name,
                        },
                    )
                )

            # 소재지 증거
            if addr:
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.CULTURAL_HERITAGE,
                        indicator="소재지",
                        value=addr,
                        unit=None,
                        observed_at=now,
                        screening_only=screening_only,
                        metadata_json={
                            "heritage_name": name,
                        },
                    )
                )

        logger.info(
            "국가유산청 정규화 완료: %d건 증거 생성 (%d개 문화재)",
            len(evidences), len(items),
        )
        return evidences

    @staticmethod
    def _kind_code_to_name(code: str) -> str:
        """문화재 종류 코드를 한글명으로 변환한다."""
        mapping = {
            "11": "국보",
            "12": "보물",
            "13": "사적",
            "14": "명승",
            "15": "천연기념물",
            "21": "시도유형문화재",
            "22": "시도무형문화재",
            "23": "시도기념물",
            "24": "시도민속문화재",
            "31": "문화재자료",
            "79": "등록문화재",
            "80": "등록유형문화재",
        }
        return mapping.get(code, code)
