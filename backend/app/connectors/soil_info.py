"""국립환경과학원 토양측정망 커넥터.

토양측정망 정보 조회 API를 통해 측정지점별 토양오염 데이터를 수집한다.
- Cd(카드뮴), Cu(구리), Pb(납), Zn(아연), Ni(니켈), Cr6+(6가크롬), pH, 유기물함량
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15081074/openapi.do
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

# 국립환경과학원 토양측정망 정보 조회 서비스 엔드포인트
SOIL_BASE_URL = (
    "http://apis.data.go.kr/1480523/SoilMeasuringService"
)


class SoilInfoConnector(BaseConnector):
    """국립환경과학원 토양측정망 커넥터."""

    connector_key = "soil_info"
    display_name = "국립환경과학원 토양측정망"

    # 지표 매핑: API 필드명 → (지표명, 단위)
    INDICATOR_MAP = {
        "ITEM_CD": ("Cd", "mg/kg"),
        "ITEM_CU": ("Cu", "mg/kg"),
        "ITEM_PB": ("Pb", "mg/kg"),
        "ITEM_ZN": ("Zn", "mg/kg"),
        "ITEM_NI": ("Ni", "mg/kg"),
        "ITEM_CR6": ("Cr6+", "mg/kg"),
        "ITEM_PH": ("pH", ""),
        "ITEM_OM": ("유기물함량", "%"),
    }

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """토양측정망 API를 호출하여 토양오염 측정 데이터를 반환한다.

        params:
            year: 조회 연도 (예: "2024") -- 필수
            site_code: 측정지점 코드 (선택)
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 페이지당 건수 (기본 100)

        Returns:
            토양측정망 API JSON 응답 원본
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

        # API 요청 파라미터 구성
        query_params: dict[str, str] = {
            "serviceKey": api_key,
            "resultType": "json",
            "year": str(year),
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(params.get("num_of_rows", 100)),
        }

        # 측정지점 코드 필터 (선택)
        site_code = params.get("site_code")
        if site_code:
            query_params["siteCode"] = site_code

        url = f"{SOIL_BASE_URL}/getSoilMeasuringList"

        logger.info(
            "토양측정망 API 호출: 연도=%s, 측정지점=%s",
            year,
            site_code or "전체",
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()

            data = response.json()

        # 응답 유효성 검사 -- 래퍼가 getSoilMeasuringList
        result = data.get("getSoilMeasuringList", {})
        header = result.get("header", {})
        result_code = header.get("code")

        if result_code != "00":
            result_msg = header.get("message", "알 수 없는 오류")
            raise RuntimeError(
                f"토양측정망 API 오류: [{result_code}] {result_msg}"
            )

        total_count = result.get("totalCount", 0)
        logger.info("토양측정망 API 응답 성공: 총 %s건", total_count)

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """토양측정망 응답을 EvidenceCreate 목록으로 변환한다.

        응답 구조:
            getSoilMeasuringList.item[] 배열에 측정 데이터가 포함됨
        """
        evidences: list[EvidenceCreate] = []

        result = raw_payload.get("getSoilMeasuringList", {})
        items = result.get("item", [])

        if not items:
            logger.warning("토양측정망 응답에 측정 데이터가 없습니다.")
            return evidences

        for item in items:
            # 측정일 파싱 -- 다양한 날짜 형식 지원
            observed_at = None
            measure_date = item.get("MEASURE_DT")
            if measure_date:
                for fmt in ("%Y.%m.%d", "%Y%m%d", "%Y-%m-%d"):
                    try:
                        observed_at = datetime.strptime(measure_date, fmt)
                        break
                    except ValueError:
                        continue
                if observed_at is None:
                    logger.warning("측정일 파싱 실패: %s", measure_date)

            site_name = item.get("PT_NM", "")
            site_code = item.get("PT_NO", "")

            for field_key, (indicator_name, unit) in self.INDICATOR_MAP.items():
                raw_value = item.get(field_key)

                # 값이 없거나 빈 문자열이면 건너뛰기
                if raw_value is None or str(raw_value).strip() == "":
                    continue

                # 공백 제거 후 수치 변환
                cleaned = str(raw_value).strip()
                numeric_val = None
                try:
                    numeric_val = float(cleaned)
                except (ValueError, TypeError):
                    pass

                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.SOIL,
                        indicator=indicator_name,
                        value=cleaned,
                        numeric_value=numeric_val,
                        unit=unit,
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "site_name": site_name,
                            "site_code": site_code,
                            "measure_date": measure_date,
                        },
                    )
                )

        logger.info(
            "토양측정망 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
