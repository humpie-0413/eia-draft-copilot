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
        "pm10Value": ("PM10", "ug/m3"),
        "pm25Value": ("PM2.5", "ug/m3"),
        "o3Value": ("O3", "ppm"),
        "no2Value": ("NO2", "ppm"),
        "so2Value": ("SO2", "ppm"),
        "coValue": ("CO", "ppm"),
    }

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """에어코리아 API를 호출하여 대기질 측정 데이터를 반환한다.

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

        # API 요청 파라미터 구성
        query_params = {
            "serviceKey": api_key,
            "returnType": "json",
            "stationName": station_name,
            "dataTerm": params.get("data_term", "DAILY"),
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(params.get("num_of_rows", 100)),
            "ver": "1.3",  # PM2.5 포함 버전
        }

        url = f"{AIRKOREA_BASE_URL}/getMsrstnAcctoRltmMesureDnsty"

        logger.info(
            "에어코리아 API 호출: 측정소=%s, 기간=%s",
            station_name,
            query_params["dataTerm"],
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()

            data = response.json()

        # 응답 유효성 검사
        resp = data.get("response", {})
        header = resp.get("header", {})
        result_code = header.get("resultCode")

        if result_code != "00":
            result_msg = header.get("resultMsg", "알 수 없는 오류")
            raise RuntimeError(
                f"에어코리아 API 오류: [{result_code}] {result_msg}"
            )

        logger.info(
            "에어코리아 API 응답 성공: 총 %s건",
            resp.get("body", {}).get("totalCount", 0),
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
