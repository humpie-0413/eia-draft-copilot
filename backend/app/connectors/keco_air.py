"""한국환경공단 대기질 커넥터 (스켈레톤).

에어코리아 API를 통해 대기오염 측정 데이터를 수집한다.
- PM10, PM2.5, O3, NO2, SO2, CO 등 대기질 지표
- 측정소별·기간별 조회

TODO: Phase 3 이후에 실제 API 호출 로직 구현 예정
"""

import uuid
from typing import Any

from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate


class KecoAirConnector(BaseConnector):
    connector_key = "keco_air"
    display_name = "한국환경공단 대기질 (에어코리아)"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """에어코리아 API를 호출하여 대기질 측정 데이터를 반환한다.

        params 예시:
            station_name: 측정소명 (예: "종로구")
            date_term: 조회 기간 ("DAILY", "MONTH", "3MONTH")
            page_no: 페이지 번호
            num_of_rows: 페이지당 건수

        TODO: 실제 httpx 호출 구현
        """
        raise NotImplementedError("커넥터 구현 예정 — Phase 3 이후 작업")

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """에어코리아 응답을 EvidenceCreate 목록으로 변환한다.

        raw_payload 구조 예시 (에어코리아 API):
            {
                "response": {
                    "body": {
                        "items": [
                            {
                                "dataTime": "2026-03-12 14:00",
                                "stationName": "종로구",
                                "pm10Value": "45",
                                "pm25Value": "22",
                                "o3Value": "0.035",
                                ...
                            }
                        ]
                    }
                }
            }

        TODO: 실제 정규화 로직 구현
        """
        # 스켈레톤 — 구조만 정의, 실제 파싱은 추후 구현
        evidences: list[EvidenceCreate] = []

        items = (
            raw_payload
            .get("response", {})
            .get("body", {})
            .get("items", [])
        )

        # 지표 매핑: API 필드명 → (지표명, 단위)
        indicator_map = {
            "pm10Value": ("PM10", "ug/m3"),
            "pm25Value": ("PM2.5", "ug/m3"),
            "o3Value": ("O3", "ppm"),
            "no2Value": ("NO2", "ppm"),
            "so2Value": ("SO2", "ppm"),
            "coValue": ("CO", "ppm"),
        }

        for item in items:
            for field_key, (indicator_name, unit) in indicator_map.items():
                raw_value = item.get(field_key)
                if raw_value is None or raw_value == "-":
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
                        screening_only=screening_only,
                        metadata_json={
                            "station_name": item.get("stationName"),
                            "data_time": item.get("dataTime"),
                        },
                    )
                )

        return evidences
