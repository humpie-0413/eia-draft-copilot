"""물환경정보시스템 수질 커넥터 (스켈레톤).

물환경정보시스템 API를 통해 수질 측정 데이터를 수집한다.
- BOD, COD, SS, T-N, T-P, DO 등 수질 지표
- 측정지점별·기간별 조회

TODO: Phase 3 이후에 실제 API 호출 로직 구현 예정
"""

import uuid
from typing import Any

from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate


class WaterInfoConnector(BaseConnector):
    connector_key = "water_info"
    display_name = "물환경정보시스템 수질"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """물환경정보시스템 API를 호출하여 수질 측정 데이터를 반환한다.

        params 예시:
            site_id: 측정지점 ID
            start_date: 조회 시작일 ("2026-01-01")
            end_date: 조회 종료일 ("2026-03-12")
            item_code: 항목 코드 ("BOD", "COD" 등)

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
        """물환경정보시스템 응답을 EvidenceCreate 목록으로 변환한다.

        raw_payload 구조 예시:
            {
                "list": [
                    {
                        "siteName": "팔당댐",
                        "measureDate": "2026-03-01",
                        "bod": "1.2",
                        "cod": "3.5",
                        "ss": "8.0",
                        "tn": "2.1",
                        "tp": "0.03",
                        "do": "9.5"
                    }
                ]
            }

        TODO: 실제 정규화 로직 구현
        """
        evidences: list[EvidenceCreate] = []

        items = raw_payload.get("list", [])

        # 지표 매핑: API 필드명 → (지표명, 단위)
        indicator_map = {
            "bod": ("BOD", "mg/L"),
            "cod": ("COD", "mg/L"),
            "ss": ("SS", "mg/L"),
            "tn": ("T-N", "mg/L"),
            "tp": ("T-P", "mg/L"),
            "do": ("DO", "mg/L"),
        }

        for item in items:
            for field_key, (indicator_name, unit) in indicator_map.items():
                raw_value = item.get(field_key)
                if raw_value is None or raw_value == "":
                    continue

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
                        category=EvidenceCategory.WATER_QUALITY,
                        indicator=indicator_name,
                        value=str(raw_value),
                        numeric_value=numeric_val,
                        unit=unit,
                        screening_only=screening_only,
                        metadata_json={
                            "site_name": item.get("siteName"),
                            "measure_date": item.get("measureDate"),
                        },
                    )
                )

        return evidences
