"""기상청 종관기상관측(ASOS) 커넥터.

기상청 지상(종관, ASOS) 일자료 조회서비스를 통해 관측소별 기상 데이터를 수집한다.
- 평균기온, 최고기온, 최저기온, 강수량, 평균풍속, 최대풍속, 평균습도
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15059093/openapi.do
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

# 기상청 지상(종관, ASOS) 일자료 조회서비스 엔드포인트
KMA_ASOS_BASE_URL = (
    "http://apis.data.go.kr/1360000/AsosDalyInfoService"
)

# 주요 ASOS 관측소 번호 참고 (stn_id)
# 108: 서울, 112: 인천, 119: 수원, 133: 대전, 143: 대구,
# 156: 광주, 159: 부산, 184: 제주, 146: 전주, 152: 울산


class KmaWeatherConnector(BaseConnector):
    """기상청 종관기상관측(ASOS) 커넥터."""

    connector_key = "kma_weather"
    display_name = "기상청 종관기상관측 (ASOS)"

    # 지표 매핑: API 필드명 → (지표명, 단위)
    INDICATOR_MAP = {
        "avgTa": ("평균기온", "\u2103"),
        "maxTa": ("최고기온", "\u2103"),
        "minTa": ("최저기온", "\u2103"),
        "sumRn": ("강수량", "mm"),
        "avgWs": ("평균풍속", "m/s"),
        "maxWs": ("최대풍속", "m/s"),
        "avgRhm": ("평균습도", "%"),
    }

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """기상청 ASOS API를 호출하여 일별 기상 관측 데이터를 반환한다.

        params:
            stn_id: 관측소 번호 (예: "108" = 서울) -- 필수
            start_dt: 조회 시작일 (YYYYMMDD, 예: "20230101") -- 필수
            end_dt: 조회 종료일 (YYYYMMDD, 예: "20231231") -- 필수
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 페이지당 건수 (기본 999)

        Returns:
            기상청 ASOS API JSON 응답 원본
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 공공데이터포털 API 키를 설정하세요."
            )

        stn_id = params.get("stn_id")
        if not stn_id:
            raise ValueError("stn_id(관측소 번호) 파라미터가 필요합니다.")

        start_dt = params.get("start_dt")
        end_dt = params.get("end_dt")
        if not start_dt or not end_dt:
            raise ValueError(
                "start_dt(시작일)와 end_dt(종료일) 파라미터가 필요합니다. "
                "형식: YYYYMMDD"
            )

        # API 요청 파라미터 구성 — 최대 50건 제한 (응답 속도 개선)
        MAX_ROWS = 50
        requested_rows = min(int(params.get("num_of_rows", MAX_ROWS)), MAX_ROWS)
        query_params: dict[str, str] = {
            "serviceKey": api_key,
            "dataType": "JSON",
            "dataCd": "ASOS",
            "dateCd": "DAY",
            "startDt": str(start_dt),
            "endDt": str(end_dt),
            "stnIds": str(stn_id),
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(requested_rows),
        }

        url = f"{KMA_ASOS_BASE_URL}/getWthrDataList"

        logger.info(
            "기상청 ASOS API 호출: 관측소=%s, 기간=%s~%s",
            stn_id,
            start_dt,
            end_dt,
        )

        # connect/read 타임아웃 분리: 연결 10초, 읽기는 전체 타임아웃
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(settings.CONNECTOR_TIMEOUT),
            write=10.0,
            pool=10.0,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
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
                f"기상청 ASOS API 오류: [{result_code}] {result_msg}"
            )

        total_count = resp.get("body", {}).get("totalCount", 0)
        logger.info("기상청 ASOS API 응답 성공: 총 %s건", total_count)

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """기상청 ASOS 응답을 EvidenceCreate 목록으로 변환한다.

        응답 구조:
            response.body.items.item[] 배열에 일별 관측 데이터가 포함됨
        """
        evidences: list[EvidenceCreate] = []

        body = raw_payload.get("response", {}).get("body", {})
        items_wrapper = body.get("items", {})

        # items가 dict이면 item 키 사용, 리스트이면 직접 사용
        if isinstance(items_wrapper, dict):
            items = items_wrapper.get("item", [])
        elif isinstance(items_wrapper, list):
            items = items_wrapper
        else:
            items = []

        if not items:
            logger.warning("기상청 ASOS 응답에 관측 데이터가 없습니다.")
            return evidences

        for item in items:
            # 관측일 파싱 -- "YYYY-MM-DD" 형식
            observed_at = None
            tm = item.get("tm")
            if tm:
                try:
                    observed_at = datetime.strptime(tm, "%Y-%m-%d")
                except ValueError:
                    logger.warning("관측일 파싱 실패: %s", tm)

            stn_nm = item.get("stnNm", "")
            stn_id = item.get("stnId", "")

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
                        category=EvidenceCategory.CLIMATE,
                        indicator=indicator_name,
                        value=cleaned,
                        numeric_value=numeric_val,
                        unit=unit,
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "station_name": stn_nm,
                            "station_id": stn_id,
                            "date": tm,
                        },
                    )
                )

        logger.info(
            "기상청 ASOS 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences
