"""V-world 토지이용계획 커넥터.

V-world 2D데이터 API를 통해 프로젝트 geometry 중심점 기준 토지이용계획을 조회한다.
- 용도지역구분, 용도지구, 지목
- V-world API 인증키 기반 호출 (VWORLD_API_KEY)
- API 문서: https://www.vworld.kr/dev/v4dv_2ddataguide2_s001.do
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate

logger = logging.getLogger(__name__)

VWORLD_DATA_URL = "https://api.vworld.kr/req/data"


class LandUseConnector(BaseConnector):
    """V-world 토지이용계획 커넥터."""

    connector_key = "vworld_land_use"
    display_name = "V-world 토지이용계획"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """V-world 2D 데이터 API를 호출하여 토지이용계획 데이터를 반환한다.

        params:
            lng: 경도 (프로젝트 geometry 중심점)
            lat: 위도 (프로젝트 geometry 중심점)
            data_type: 조회 데이터 유형 (기본: "LT_C_LHBLPN")

        Returns:
            V-world API JSON 응답 원본
        """
        api_key = settings.VWORLD_API_KEY
        if not api_key:
            raise ValueError(
                "VWORLD_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 V-world API 키를 설정하세요."
            )

        lng = params.get("lng")
        lat = params.get("lat")
        if lng is None or lat is None:
            raise ValueError("lng(경도)와 lat(위도) 파라미터가 필요합니다.")

        # 토지이용계획도: LT_C_LHBLPN (토지이용규제기본법 토지이용계획)
        data_type = params.get("data_type", "LT_C_LHBLPN")

        query_params: dict[str, str] = {
            "service": "data",
            "request": "GetFeature",
            "data": data_type,
            "key": api_key,
            "domain": "",
            "geomFilter": f"POINT({lng} {lat})",
            "crs": "EPSG:4326",
            "format": "json",
            "size": "100",
        }

        logger.info(
            "V-world 토지이용계획 API 호출: 좌표=(%s, %s), data=%s",
            lat, lng, data_type,
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(VWORLD_DATA_URL, params=query_params)
            response.raise_for_status()
            data = response.json()

        # 응답 유효성 검사
        resp = data.get("response", {})
        status = resp.get("status", "")

        if status != "OK":
            error_msg = resp.get("error", {}).get("text", "알 수 없는 오류")
            raise RuntimeError(
                f"V-world API 오류: [{status}] {error_msg}"
            )

        total = resp.get("record", {}).get("total", 0)
        logger.info("V-world API 응답 성공: 총 %s건", total)

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """V-world 응답을 EvidenceCreate 목록으로 변환한다."""
        evidences: list[EvidenceCreate] = []

        resp = raw_payload.get("response", {})
        result = resp.get("result", {})
        features = result.get("featureCollection", {}).get("features", [])

        if not features:
            logger.warning("V-world 응답에 토지이용 데이터가 없습니다.")
            return evidences

        # 용도지역 정보 추출
        zone_names: list[str] = []
        district_names: list[str] = []
        jimok_names: list[str] = []

        for feature in features:
            props = feature.get("properties", {})
            # 용도지역구분명
            prps_nm = props.get("PRPOS_AREA_NM") or props.get("prposAreaNm", "")
            if prps_nm and prps_nm not in zone_names:
                zone_names.append(prps_nm)
            # 지목
            jimok = props.get("JIMOK") or props.get("jimok", "")
            if jimok and jimok not in jimok_names:
                jimok_names.append(jimok)

        now = datetime.now(tz=timezone.utc)

        if zone_names:
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="용도지역구분",
                    value=", ".join(zone_names),
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "V-world 토지이용계획",
                        "zone_count": len(zone_names),
                        "zones": zone_names,
                    },
                )
            )

        if jimok_names:
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="지목",
                    value=", ".join(jimok_names),
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "V-world 토지이용계획",
                        "jimok_count": len(jimok_names),
                    },
                )
            )

        # 용도지구 (feature 수 기반)
        if features:
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="용도지구",
                    value=f"토지이용규제 {len(features)}건 조회",
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "V-world 토지이용계획",
                        "feature_count": len(features),
                    },
                )
            )

        logger.info(
            "V-world 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
