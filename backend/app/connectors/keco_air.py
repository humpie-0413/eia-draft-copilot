"""한국환경공단 대기질 커넥터 (에어코리아 실제 연동).

에어코리아 대기오염정보 조회 API를 통해 측정소별 대기질 데이터를 수집한다.
- PM10, PM2.5, O3, NO2, SO2, CO 6개 지표
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15073861/openapi.do
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate

logger = logging.getLogger(__name__)

# 에어코리아 측정소별 실시간 측정정보 조회 API
AIRKOREA_BASE_URL = (
    "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"
)


class KecoAirConnector(BaseConnector):
    connector_key = "keco_air"
    display_name = "한국환경공단 대기질 (에어코리아)"

    # 지표 매핑: API 필드명 → (지표명, 단위)
    INDICATOR_MAP = {
        "pm10Value": ("PM10_연평균", "ug/m3"),
        "pm25Value": ("PM2.5_연평균", "ug/m3"),
        "o3Value": ("O3_연평균", "ppm"),
        "no2Value": ("NO2_연평균", "ppm"),
        "so2Value": ("SO2_연평균", "ppm"),
        "coValue": ("CO_연평균", "ppm"),
    }

    # 측정소명에서 제거할 행정구역 접미사 목록
    _STATION_SUFFIXES = ("특별자치시", "특별시", "광역시", "시", "군", "구", "읍", "면", "동", "리")

    def _generate_station_name_variants(self, name: str) -> list[str]:
        """측정소명 후보 목록 생성 (원본 + 접미사 제거 변형).

        에어코리아 측정소명은 행정구역 접미사 없이 등록된 경우가 많다.
        예: "양평군" → ["양평군", "양평"], "세종시" → ["세종시", "세종"]
        """
        variants = [name]
        for suffix in self._STATION_SUFFIXES:
            if name.endswith(suffix) and len(name) > len(suffix):
                stripped = name[: -len(suffix)]
                if stripped and stripped not in variants:
                    variants.append(stripped)
        return variants

    async def _fetch_single(
        self,
        client: httpx.AsyncClient,
        station_name: str,
        params: dict[str, Any],
        api_key: str,
    ) -> dict[str, Any] | None:
        """단일 측정소명으로 에어코리아 API를 호출한다.

        데이터가 있으면 응답 dict, 없거나 오류면 None 반환.
        """
        query_params = {
            "serviceKey": api_key,
            "returnType": "json",
            "stationName": station_name,
            "dataTerm": params.get("data_term", "DAILY"),
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(params.get("num_of_rows", 100)),
            "ver": "1.3",
        }

        url = f"{AIRKOREA_BASE_URL}/getMsrstnAcctoRltmMesureDnsty"

        logger.info(
            "에어코리아 API 호출: 측정소=%s, 기간=%s",
            station_name,
            query_params["dataTerm"],
        )

        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.warning("에어코리아 API 호출 실패 (측정소=%s): %s", station_name, e)
            return None

        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")

        if result_code != "00":
            logger.warning(
                "에어코리아 API 오류 (측정소=%s): [%s] %s",
                station_name,
                result_code,
                header.get("resultMsg", ""),
            )
            return None

        total_count = resp.get("body", {}).get("totalCount", 0)
        items = resp.get("body", {}).get("items", [])

        if not total_count or not items:
            logger.info("에어코리아 응답 데이터 0건 (측정소=%s)", station_name)
            return None

        logger.info(
            "에어코리아 API 응답 성공: 측정소=%s, 총 %s건",
            station_name,
            total_count,
        )
        return data

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """에어코리아 API를 호출하여 대기질 측정 데이터를 반환한다.

        측정소명이 정확히 일치하지 않을 경우, 행정구역 접미사를 제거한
        변형 이름으로 재시도한다.
        예: "양평군" → "양평", "세종시" → "세종", "보령시" → "보령"

        params:
            station_name: 측정소명 (예: "종로구") — 필수
            data_term: 조회 기간 ("DAILY"=1일, "MONTH"=1개월, "3MONTH"=3개월)
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 페이지당 건수 (기본 100)

        Returns:
            에어코리아 JSON 응답 원본
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 공공데이터포털 API 키를 설정하세요."
            )

        station_name = params.get("station_name")
        if not station_name:
            raise ValueError("station_name(측정소명) 파라미터가 필요합니다.")

        # 측정소명 변형 목록 생성 (원본 + 접미사 제거)
        variants = self._generate_station_name_variants(station_name)

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            for variant in variants:
                data = await self._fetch_single(client, variant, params, api_key)
                if data is not None:
                    if variant != station_name:
                        logger.info(
                            "측정소명 변형으로 데이터 수신 성공: '%s' → '%s'",
                            station_name,
                            variant,
                        )
                    return data

        # 모든 변형이 실패한 경우, 빈 응답 구조 반환
        logger.warning(
            "에어코리아: 모든 측정소명 변형 시도 실패 — %s", variants
        )
        return {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
                "body": {"totalCount": 0, "items": []},
            }
        }

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """에어코리아 응답을 EvidenceCreate 목록으로 변환한다.

        에어코리아 응답 구조:
            response.body.items[] 배열에 측정 데이터가 포함됨
        """
        evidences: list[EvidenceCreate] = []

        # items 추출 — 응답 구조에 따라 리스트 또는 None일 수 있음
        body = raw_payload.get("response", {}).get("body", {})
        items = body.get("items", [])

        # items가 None이거나 빈 경우
        if not items:
            logger.warning("에어코리아 응답에 측정 데이터가 없습니다.")
            return evidences

        for item in items:
            # 측정 시각 파싱
            observed_at = None
            data_time = item.get("dataTime")
            if data_time:
                try:
                    observed_at = datetime.strptime(
                        data_time, "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    logger.warning("측정 시각 파싱 실패: %s", data_time)

            station_name = item.get("stationName", "")

            for field_key, (indicator_name, unit) in self.INDICATOR_MAP.items():
                raw_value = item.get(field_key)

                # 값이 없거나 "-" 또는 통신 오류인 경우 건너뛰기
                if raw_value is None or str(raw_value).strip() in ("-", "", "통신장애"):
                    continue

                # 수치 변환 시도
                numeric_val = None
                try:
                    numeric_val = float(raw_value)
                except (ValueError, TypeError):
                    pass

                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.AIR_QUALITY,
                        indicator=indicator_name,
                        value=str(raw_value),
                        numeric_value=numeric_val,
                        unit=unit,
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "station_name": station_name,
                            "data_time": data_time,
                            "grade": item.get(
                                field_key.replace("Value", "Grade")
                            ),
                        },
                    )
                )

        logger.info(
            "에어코리아 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
