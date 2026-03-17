"""V-world 토지이용계획 커넥터.

V-world 2D데이터 API를 통해 프로젝트 geometry 중심점 기준 토지이용계획을 조회한다.
- 용도지역: LT_C_UQ111 (도시지역 용도지역)
- 지목/토지이용: LT_C_LHBLPN (토지이용규제기본법)
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

# 조회 대상 데이터 타입
DATA_TYPES = {
    "LT_C_UQ111": "용도지역(도시지역)",
    "LT_C_LHBLPN": "토지이용계획",
}


class LandUseConnector(BaseConnector):
    """V-world 토지이용계획 커넥터."""

    connector_key = "vworld_land_use"
    display_name = "V-world 토지이용계획"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """V-world 2D 데이터 API를 호출하여 토지이용계획 데이터를 반환한다.

        params:
            lng: 경도 (프로젝트 geometry 중심점)
            lat: 위도 (프로젝트 geometry 중심점)

        Returns:
            복수 데이터 타입 조회 결과를 병합한 딕셔너리
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

        logger.info(
            "V-world 토지이용계획 API 호출: 좌표=(%s, %s)",
            lat, lng,
        )

        # 좌표 그리드: 중심점 실패 시 주변 8지점(±0.005° ≈ 500m) 추가 시도
        # 보령 등 비도시지역에서 0.002° 그리드로 불충분한 사례 대응
        OFFSET = 0.005
        _lng, _lat = float(lng), float(lat)
        coordinate_candidates = [
            (_lng, _lat),                                # 중심점
            (_lng + OFFSET, _lat),                       # 동
            (_lng - OFFSET, _lat),                       # 서
            (_lng, _lat + OFFSET),                       # 북
            (_lng, _lat - OFFSET),                       # 남
            (_lng + OFFSET, _lat + OFFSET),              # 북동
            (_lng - OFFSET, _lat + OFFSET),              # 북서
            (_lng + OFFSET, _lat - OFFSET),              # 남동
            (_lng - OFFSET, _lat - OFFSET),              # 남서
        ]

        all_features: dict[str, list[dict]] = {}
        used_lng, used_lat = float(lng), float(lat)

        timeout = httpx.Timeout(
            connect=10.0,
            read=float(settings.CONNECTOR_TIMEOUT),
            write=10.0,
            pool=10.0,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            for coord_idx, (try_lng, try_lat) in enumerate(coordinate_candidates):
                coord_features: dict[str, list[dict]] = {}

                for data_type, desc in DATA_TYPES.items():
                    query_params: dict[str, str] = {
                        "service": "data",
                        "request": "GetFeature",
                        "data": data_type,
                        "key": api_key,
                        "domain": "",
                        "geomFilter": f"POINT({try_lng} {try_lat})",
                        "crs": "EPSG:4326",
                        "format": "json",
                        "size": "100",
                    }

                    try:
                        response = await client.get(
                            VWORLD_DATA_URL, params=query_params,
                        )
                        response.raise_for_status()
                        data = response.json()

                        resp = data.get("response", {})
                        status = resp.get("status", "")

                        if status == "OK":
                            features = (
                                resp.get("result", {})
                                .get("featureCollection", {})
                                .get("features", [])
                            )
                            coord_features[data_type] = features
                            logger.info(
                                "V-world %s 응답 성공: %d건 (좌표 %d번)",
                                desc, len(features), coord_idx,
                            )
                        else:
                            logger.info(
                                "V-world %s: status=%s (데이터 없음, 좌표 %d번)",
                                desc, status, coord_idx,
                            )
                            coord_features[data_type] = []
                    except Exception as e:
                        logger.warning(
                            "V-world %s 조회 실패 (좌표 %d번): %s",
                            desc, coord_idx, e,
                        )
                        coord_features[data_type] = []

                coord_total = sum(len(v) for v in coord_features.values())
                if coord_total > 0:
                    all_features = coord_features
                    used_lng, used_lat = try_lng, try_lat
                    if coord_idx > 0:
                        logger.info(
                            "V-world 중심점 대신 오프셋 좌표 사용: "
                            "(%.6f, %.6f) → (%.6f, %.6f)",
                            float(lng), float(lat), try_lng, try_lat,
                        )
                    break

                if coord_idx == 0:
                    logger.info(
                        "V-world 중심점에서 데이터 없음, 주변 좌표 탐색 시작"
                    )

        total = sum(len(v) for v in all_features.values())
        if total == 0:
            # 모든 좌표에서 토지이용 데이터가 없는 경우
            logger.warning(
                "V-world API 응답에 토지이용 데이터가 없습니다: 좌표=(%s, %s). "
                "비도시지역이거나 좌표가 필지 경계 밖일 수 있습니다. "
                "(주변 %d지점 탐색 완료)",
                lat, lng, len(coordinate_candidates),
            )

        logger.info("V-world API 총 %d건 수집", total)
        return {
            "features_by_type": all_features,
            "lng": str(used_lng),
            "lat": str(used_lat),
        }

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
        now = datetime.now(tz=timezone.utc)

        features_by_type = raw_payload.get("features_by_type", {})

        # --- LT_C_UQ111: 용도지역(도시지역) ---
        uq111_features = features_by_type.get("LT_C_UQ111", [])
        zone_names: list[str] = []
        for feature in uq111_features:
            props = feature.get("properties", {})
            uname = props.get("uname", "")
            if uname and uname not in zone_names:
                zone_names.append(uname)

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
                        "source": "V-world LT_C_UQ111",
                        "zone_count": len(zone_names),
                        "zones": zone_names,
                    },
                )
            )

        # --- LT_C_LHBLPN: 토지이용계획 (지목 등) ---
        lhblpn_features = features_by_type.get("LT_C_LHBLPN", [])
        jimok_names: list[str] = []
        prps_names: list[str] = []

        for feature in lhblpn_features:
            props = feature.get("properties", {})
            jimok = (
                props.get("JIMOK") or props.get("jimok", "")
            )
            if jimok and jimok not in jimok_names:
                jimok_names.append(jimok)

            prps_nm = (
                props.get("PRPOS_AREA_NM")
                or props.get("prposAreaNm", "")
            )
            if prps_nm and prps_nm not in prps_names:
                prps_names.append(prps_nm)

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
                        "source": "V-world LT_C_LHBLPN",
                        "jimok_count": len(jimok_names),
                    },
                )
            )

        # LT_C_LHBLPN에서 용도지역 정보가 있고, UQ111에서 없는 경우 fallback
        if prps_names and not zone_names:
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="용도지역구분",
                    value=", ".join(prps_names),
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "V-world LT_C_LHBLPN (fallback)",
                        "zone_count": len(prps_names),
                    },
                )
            )

        # 용도지구 요약
        total_features = len(uq111_features) + len(lhblpn_features)
        if total_features > 0:
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="용도지구",
                    value=f"토지이용규제 {total_features}건 조회",
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "V-world",
                        "feature_count": total_features,
                    },
                )
            )

        logger.info(
            "V-world 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
