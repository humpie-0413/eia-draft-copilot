"""물환경정보시스템 수질 커넥터 (실제 연동).

물환경정보시스템 수질측정정보 API를 통해 측정지점별 수질 데이터를 수집한다.
- BOD, COD, SS, DO, T-N, T-P 6개 지표
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15009370/openapi.do
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

# 수질측정정보 조회 API
WATER_INFO_BASE_URL = (
    "http://apis.data.go.kr/1480523/WaterQualityService"
)


class WaterInfoConnector(BaseConnector):
    connector_key = "water_info"
    display_name = "물환경정보시스템 수질"

    # 지표 매핑: API 필드명 → (지표명, 단위)
    INDICATOR_MAP = {
        "bod": ("BOD", "mg/L"),
        "cod": ("COD", "mg/L"),
        "ss": ("SS", "mg/L"),
        "do_": ("DO", "mg/L"),
        "tn": ("T-N", "mg/L"),
        "tp": ("T-P", "mg/L"),
    }

    # API 응답 필드명 (do_는 파이썬 예약어 회피용, 실제 API 필드는 "do")
    FIELD_ALIASES = {
        "do_": "do",
    }

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """물환경정보시스템 API를 호출하여 수질 측정 데이터를 반환한다.

        params:
            site_id: 측정지점 코드 (예: "3008A70") — 필수
            start_date: 조회 시작일 ("2026-01-01") — 필수
            end_date: 조회 종료일 ("2026-03-12") — 필수
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 페이지당 건수 (기본 100)

        Returns:
            수질 API JSON 응답 원본
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 공공데이터포털 API 키를 설정하세요."
            )

        site_id = params.get("site_id")
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        if not site_id:
            raise ValueError("site_id(측정지점 코드) 파라미터가 필요합니다.")
        if not start_date or not end_date:
            raise ValueError(
                "start_date(시작일)와 end_date(종료일) 파라미터가 필요합니다."
            )

        # API 요청 파라미터 구성
        query_params = {
            "serviceKey": api_key,
            "resultType": "json",
            "ptNoList": site_id,
            "stDt": start_date.replace("-", ""),  # YYYYMMDD 형식
            "edDt": end_date.replace("-", ""),
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(params.get("num_of_rows", 100)),
        }

        url = f"{WATER_INFO_BASE_URL}/getWaterMeasuringList"

        logger.info(
            "물환경정보 API 호출: 측정지점=%s, 기간=%s~%s",
            site_id,
            start_date,
            end_date,
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
                f"물환경정보 API 오류: [{result_code}] {result_msg}"
            )

        total_count = resp.get("body", {}).get("totalCount", 0)
        logger.info("물환경정보 API 응답 성공: 총 %s건", total_count)

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """물환경정보시스템 응답을 EvidenceCreate 목록으로 변환한다.

        응답 구조:
            response.body.items[] 배열에 측정 데이터가 포함됨
        """
        evidences: list[EvidenceCreate] = []

        body = raw_payload.get("response", {}).get("body", {})
        items = body.get("items", [])

        if not items:
            logger.warning("물환경정보 응답에 측정 데이터가 없습니다.")
            return evidences

        for item in items:
            # 측정일 파싱
            observed_at = None
            measure_date = item.get("wmyrMd") or item.get("mesuDt")
            if measure_date:
                try:
                    # YYYYMMDD 또는 YYYY-MM-DD 형식 모두 처리
                    clean_date = measure_date.replace("-", "")
                    observed_at = datetime.strptime(clean_date, "%Y%m%d")
                except ValueError:
                    logger.warning("측정일 파싱 실패: %s", measure_date)

            site_name = item.get("ptNm", "")
            site_id = item.get("ptNo", "")

            for field_key, (indicator_name, unit) in self.INDICATOR_MAP.items():
                # API 필드명 변환 (do_ → do)
                api_field = self.FIELD_ALIASES.get(field_key, field_key)
                raw_value = item.get(api_field)

                # 값이 없거나 빈 문자열이면 건너뛰기
                if raw_value is None or str(raw_value).strip() == "":
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
                        category=EvidenceCategory.WATER_QUALITY,
                        indicator=indicator_name,
                        value=str(raw_value),
                        numeric_value=numeric_val,
                        unit=unit,
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "site_name": site_name,
                            "site_id": site_id,
                            "measure_date": measure_date,
                        },
                    )
                )

        logger.info(
            "물환경정보 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
