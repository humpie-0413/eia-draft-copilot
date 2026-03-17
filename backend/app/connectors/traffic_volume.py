"""한국건설기술연구원 교통량 통계 커넥터.

국토교통부_한국건설기술연구원 교통량 통계 데이터 정보조회서비스를 통해
도로유형별 교통량 데이터를 수집한다.
- 연도별 차종별 통계 (vt_yearly): spot_id별 total_count (연간 총 교통량)
- AADT = total_count / 365 (연평균일교통량)
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15097077/openapi.do
"""

import logging
import uuid
from typing import Any

import httpx

from app.config import settings
from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate

logger = logging.getLogger(__name__)

# 한국건설기술연구원 교통량 통계 데이터 정보조회서비스
KICT_TMS_BASE_URL = "https://apis.data.go.kr/1613000/KictTmsStat"

# 도로유형 코드 매핑
ROAD_TYPE_MAP = {
    1: "고속도로",
    2: "일반국도",
    3: "지방도",
    5: "국가지원지방도",
}

# 차종 코드 매핑 (vt_yearly 응답의 vehicle_type1~12)
VEHICLE_TYPE_MAP = {
    "vehicle_type1": "승용차",
    "vehicle_type2": "승합_소형",
    "vehicle_type3": "화물_소형",
    "vehicle_type4": "화물_중형",
    "vehicle_type5": "화물_대형",
    "vehicle_type6": "특수차",
}


class TrafficVolumeConnector(BaseConnector):
    """한국건설기술연구원 교통량 통계 커넥터."""

    connector_key = "traffic_volume"
    display_name = "한국건설기술연구원 교통량 통계 (KICT)"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """교통량 통계 API를 호출하여 도로유형별 교통량 데이터를 반환한다.

        params:
            year: 조회 연도 (예: 2023) — 필수
            dtype: 도로유형 (1=고속도로, 2=일반국도, 3=지방도, 5=국가지원지방도, 기본: 2)
            spot_id: 지점 ID (기본: "all")
            page_no: 페이지 번호 (기본: 0)
            num_of_rows: 페이지당 건수 (기본: 100)

        Returns:
            교통량 통계 JSON 응답 원본
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 공공데이터포털 API 키를 설정하세요."
            )

        year = params.get("year")
        if not year:
            raise ValueError("year(조회 연도) 파라미터가 필요합니다.")

        dtype = int(params.get("dtype", 2))

        # 최대 50건 제한 (메모리 최적화)
        MAX_ROWS = 50
        requested_rows = min(int(params.get("num_of_rows", MAX_ROWS)), MAX_ROWS)
        query_params = {
            "serviceKey": api_key,
            "output": "json",
            "year": str(year),
            "dtype": str(dtype),
            "spot_id": str(params.get("spot_id", "all")),
            "numOfRows": str(requested_rows),
            "pageNo": str(params.get("page_no", 0)),
        }

        # 연도별 차종별 통계 조회 — 올바른 오퍼레이션: /vt_yearly
        url = f"{KICT_TMS_BASE_URL}/vt_yearly"

        logger.info(
            "교통량 통계 API 호출: 연도=%s, 도로유형=%s(%s)",
            year,
            dtype,
            ROAD_TYPE_MAP.get(dtype, "기타"),
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()

            data = response.json()

        # 응답 유효성 검사
        result_code = data.get("resultCode")
        if result_code and str(result_code) != "0" and str(result_code) != "00":
            result_msg = data.get("resultMsg", "알 수 없는 오류")
            raise RuntimeError(
                f"교통량 통계 API 오류: [{result_code}] {result_msg}"
            )

        logger.info(
            "교통량 통계 API 응답 성공: %s건",
            data.get("count", 0),
        )

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """교통량 통계 응답을 EvidenceCreate 목록으로 변환한다.

        실제 응답 구조 (vt_yearly):
            {
                "resultCode": "00",
                "resultMsg": "NORMAL SERVICE",
                "year": 2023, "dtype": 2, "count": 1026,
                "traffic": [
                    {"spot_id": "0101-000", "direction": 1,
                     "vehicle_type1": ..., "total_count": 3753640},
                    ...
                ]
            }
        """
        evidences: list[EvidenceCreate] = []

        # 응답에서 교통량 데이터 추출
        items = self._extract_items(raw_payload)
        if not items:
            logger.warning("교통량 통계 응답에 교통량 데이터가 없습니다.")
            return evidences

        dtype = raw_payload.get("dtype", 2)
        year = raw_payload.get("year")
        road_type_name = ROAD_TYPE_MAP.get(int(dtype) if dtype else 2, "일반국도")

        # spot_id별로 양방향(direction 1,2) 합산하여 AADT 계산
        spot_totals: dict[str, int] = {}
        for item in items:
            spot_id = str(item.get("spot_id", ""))
            total_count = item.get("total_count", 0)
            if spot_id:
                spot_totals[spot_id] = (
                    spot_totals.get(spot_id, 0) + int(total_count)
                )

        for spot_id, yearly_total in spot_totals.items():
            # AADT = 연간 총 교통량 / 365
            aadt = round(yearly_total / 365)

            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.TRAFFIC,
                    indicator="교통량_현황",
                    value=str(aadt),
                    numeric_value=float(aadt),
                    unit="대/일",
                    observed_at=None,
                    screening_only=screening_only,
                    metadata_json={
                        "spot_id": spot_id,
                        "road_type": road_type_name,
                        "year": str(year) if year else "",
                        "yearly_total": yearly_total,
                    },
                )
            )

            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.TRAFFIC,
                    indicator="도로등급",
                    value=road_type_name,
                    numeric_value=None,
                    unit="",
                    observed_at=None,
                    screening_only=screening_only,
                    metadata_json={
                        "spot_id": spot_id,
                        "road_type": road_type_name,
                    },
                )
            )

        logger.info(
            "교통량 통계 정규화 완료: %d건 증거 생성 (%d개 지점)",
            len(evidences), len(spot_totals),
        )
        return evidences

    @staticmethod
    def _extract_items(raw_payload: dict[str, Any]) -> list[dict]:
        """다양한 응답 구조에서 교통량 항목 목록을 추출한다."""
        # 패턴 1 (실제 응답): { traffic: [...] }
        traffic = raw_payload.get("traffic")
        if isinstance(traffic, list):
            return traffic

        # 패턴 2: { response: { body: { items: [...] } } }
        body = raw_payload.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, list) and items:
            return items
        if isinstance(items, dict):
            item_list = items.get("item", [])
            if isinstance(item_list, list):
                return item_list

        # 패턴 3: { items: [...] }
        items = raw_payload.get("items", [])
        if isinstance(items, list):
            return items

        # 패턴 4: { data: [...] }
        data = raw_payload.get("data", [])
        if isinstance(data, list):
            return data

        return []
