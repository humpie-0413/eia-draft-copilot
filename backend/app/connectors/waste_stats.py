"""행정안전부 생활쓰레기배출정보 커넥터.

행정안전부_생활쓰레기배출정보 조회서비스를 통해
시군구별 생활쓰레기 배출 현황 데이터를 수집한다.
- 시군구별 생활폐기물, 음식물쓰레기, 재활용품 배출 정보
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15155080/openapi.do
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

# 행정안전부 생활쓰레기배출정보 조회서비스
WASTE_INFO_BASE_URL = (
    "http://apis.data.go.kr/1741000/household_waste_info"
)


class WasteStatsConnector(BaseConnector):
    """행정안전부 생활쓰레기배출정보 커넥터."""

    connector_key = "waste_stats"
    display_name = "행정안전부 생활쓰레기배출정보"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """생활쓰레기배출정보 API를 호출하여 지역별 폐기물 배출 데이터를 반환한다.

        params:
            region: 시군구명 (예: "강남구", "서울") — 필수
            start_date: 기준일 시작 (YYYYMMDD, 선택)
            end_date: 기준일 종료 (YYYYMMDD, 선택)
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 페이지당 건수 (기본 100)

        Returns:
            생활쓰레기배출정보 JSON 응답 원본
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 공공데이터포털 API 키를 설정하세요."
            )

        region = params.get("region")
        if not region:
            raise ValueError("region(시군구명) 파라미터가 필요합니다.")

        query_params: dict[str, str] = {
            "serviceKey": api_key,
            "returnType": "json",
            "pageNo": str(params.get("page_no", 1)),
            "numOfRows": str(params.get("num_of_rows", 10)),
            "cond[SGG_NM::LIKE]": region,
        }

        # 기간 필터 (선택)
        start_date = params.get("start_date")
        if start_date:
            query_params["cond[DAT_CRTR_YMD::GTE]"] = str(start_date)
        end_date = params.get("end_date")
        if end_date:
            query_params["cond[DAT_CRTR_YMD::LT]"] = str(end_date)

        url = f"{WASTE_INFO_BASE_URL}/info"

        logger.info(
            "생활쓰레기배출정보 API 호출: 지역=%s",
            region,
        )

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()

            data = response.json()

            # SGG_NM 검색 결과가 0건이면 CTPV_NM으로 fallback 검색
            # (세종특별자치시처럼 기초자치단체가 없는 경우 SGG_NM="없음")
            body = data.get("response", {}).get("body", {})
            if "totalCount" in body and body["totalCount"] == 0:
                logger.info(
                    "SGG_NM 검색 결과 0건 — CTPV_NM fallback 시도: %s",
                    region,
                )
                fallback_params = dict(query_params)
                del fallback_params["cond[SGG_NM::LIKE]"]
                fallback_params["cond[CTPV_NM::LIKE]"] = region
                response = await client.get(url, params=fallback_params)
                response.raise_for_status()
                data = response.json()

        # 응답 유효성 검사
        header = data.get("header", data.get("response", {}).get("header", {}))
        result_code = header.get("resultCode", header.get("code"))

        if result_code and str(result_code) not in ("00", "0", None):
            result_msg = header.get("resultMsg", header.get("message", "알 수 없는 오류"))
            raise RuntimeError(
                f"생활쓰레기배출정보 API 오류: [{result_code}] {result_msg}"
            )

        total_count = data.get("totalCount", data.get("matchCount", 0))
        logger.info("생활쓰레기배출정보 API 응답 성공: 총 %s건", total_count)

        return data

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """생활쓰레기배출정보 응답을 EvidenceCreate 목록으로 변환한다."""
        evidences: list[EvidenceCreate] = []

        items = self._extract_items(raw_payload)
        if not items:
            logger.warning("생활쓰레기배출정보 응답에 데이터가 없습니다.")
            return evidences

        for item in items:
            # 기준일 파싱
            observed_at = None
            date_str = (
                item.get("DAT_CRTR_YMD")
                or item.get("dat_crtr_ymd")
                or item.get("baseDate")
            )
            if date_str:
                try:
                    cleaned_date = str(date_str).replace("-", "").strip()
                    if len(cleaned_date) == 8:
                        observed_at = datetime.strptime(cleaned_date, "%Y%m%d")
                except ValueError:
                    logger.warning("기준일 파싱 실패: %s", date_str)

            # 시군구명 추출
            region_name = (
                item.get("SGG_NM")
                or item.get("sgg_nm")
                or item.get("regionName")
                or ""
            )

            # 생활쓰레기 배출량
            waste_amount = (
                item.get("TOT_DSCG_QTY")
                or item.get("tot_dscg_qty")
                or item.get("totalDischargeQty")
            )
            if waste_amount is not None:
                numeric_val = self._parse_numeric(waste_amount)
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="생활폐기물_발생량",
                        value=str(waste_amount).strip(),
                        numeric_value=numeric_val,
                        unit="톤/일",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "region": region_name,
                            "date": str(date_str) if date_str else "",
                        },
                    )
                )

            # 음식물쓰레기 배출량
            food_waste = (
                item.get("FOOD_DSCG_QTY")
                or item.get("food_dscg_qty")
                or item.get("foodWasteQty")
            )
            if food_waste is not None:
                numeric_val = self._parse_numeric(food_waste)
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="음식물쓰레기_발생량",
                        value=str(food_waste).strip(),
                        numeric_value=numeric_val,
                        unit="톤/일",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "region": region_name,
                            "date": str(date_str) if date_str else "",
                        },
                    )
                )

            # 재활용품 배출량
            recycle_amount = (
                item.get("RCYCLNG_QTY")
                or item.get("rcyclng_qty")
                or item.get("recyclingQty")
            )
            if recycle_amount is not None:
                numeric_val = self._parse_numeric(recycle_amount)
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="재활용_발생량",
                        value=str(recycle_amount).strip(),
                        numeric_value=numeric_val,
                        unit="톤/일",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json={
                            "region": region_name,
                            "date": str(date_str) if date_str else "",
                        },
                    )
                )

            # ──────────────────────────────────────────────────────────
            # 배출 일정/관리 정보 — 실제 행정안전부 API 응답 필드
            # (TOT_DSCG_QTY 등 발생량 필드가 없는 API 버전에서 반환됨)
            # ──────────────────────────────────────────────────────────

            # 시도명 추출 (메타데이터용)
            sido_name = (
                item.get("CTPV_NM")
                or item.get("ctpv_nm")
                or ""
            )

            # 공통 메타데이터 — 지역 정보 포함
            schedule_meta = {
                "region": region_name,
                "sido": sido_name,
                "date": str(date_str) if date_str else "",
            }

            # 관리부서 (MNG_DEPT_NM)
            mng_dept = item.get("MNG_DEPT_NM") or item.get("mng_dept_nm")
            if mng_dept and str(mng_dept).strip():
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="폐기물_관리부서",
                        value=str(mng_dept).strip(),
                        numeric_value=None,
                        unit="",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json=schedule_meta,
                    )
                )

            # 배출장소 (EMSN_PLC)
            emsn_plc = item.get("EMSN_PLC") or item.get("emsn_plc")
            if emsn_plc and str(emsn_plc).strip():
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="폐기물_배출방법",
                        value=str(emsn_plc).strip(),
                        numeric_value=None,
                        unit="",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json=schedule_meta,
                    )
                )

            # 음식물쓰레기 배출요일 (FOD_WST_EMSN_DOW)
            fod_dow = item.get("FOD_WST_EMSN_DOW") or item.get("fod_wst_emsn_dow")
            if fod_dow and str(fod_dow).strip():
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="음식물쓰레기_배출요일",
                        value=str(fod_dow).strip(),
                        numeric_value=None,
                        unit="",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json=schedule_meta,
                    )
                )

            # 재활용 배출요일 (RCYCL_EMSN_DOW)
            rcycl_dow = item.get("RCYCL_EMSN_DOW") or item.get("rcycl_emsn_dow")
            if rcycl_dow and str(rcycl_dow).strip():
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="재활용_배출요일",
                        value=str(rcycl_dow).strip(),
                        numeric_value=None,
                        unit="",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json=schedule_meta,
                    )
                )

            # 생활쓰레기 배출요일 (LF_WST_EMSN_DOW)
            lf_dow = item.get("LF_WST_EMSN_DOW") or item.get("lf_wst_emsn_dow")
            if lf_dow and str(lf_dow).strip():
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="생활쓰레기_배출요일",
                        value=str(lf_dow).strip(),
                        numeric_value=None,
                        unit="",
                        observed_at=observed_at,
                        screening_only=screening_only,
                        metadata_json=schedule_meta,
                    )
                )

        # ── 폐기물 종류 파생: 배출 일정에서 폐기물 종류를 추출한다 ──
        # 생활쓰레기, 음식물쓰레기, 재활용이 존재하면 폐기물_종류 증거를 생성
        if items and not any(e.indicator == "폐기물_종류" for e in evidences):
            waste_types: list[str] = []
            first_item = items[0]
            first_observed = None
            first_region = ""
            first_date_str = ""

            # 첫 번째 항목에서 기준 메타데이터 추출
            d = (
                first_item.get("DAT_CRTR_YMD")
                or first_item.get("dat_crtr_ymd")
                or ""
            )
            first_date_str = str(d) if d else ""
            first_region = (
                first_item.get("SGG_NM")
                or first_item.get("sgg_nm")
                or first_item.get("CTPV_NM")
                or first_item.get("ctpv_nm")
                or ""
            )
            if first_date_str:
                try:
                    cd = first_date_str.replace("-", "").strip()
                    if len(cd) == 8:
                        first_observed = datetime.strptime(cd, "%Y%m%d")
                except ValueError:
                    pass

            # 배출 항목 존재 여부로 종류 판정
            for item in items:
                lf = item.get("LF_WST_EMSN_DOW") or item.get("lf_wst_emsn_dow")
                if lf and "생활폐기물" not in waste_types:
                    waste_types.append("생활폐기물")
                fod = item.get("FOD_WST_EMSN_DOW") or item.get("fod_wst_emsn_dow")
                if fod and "음식물쓰레기" not in waste_types:
                    waste_types.append("음식물쓰레기")
                rcycl = item.get("RCYCL_EMSN_DOW") or item.get("rcycl_emsn_dow")
                if rcycl and "재활용" not in waste_types:
                    waste_types.append("재활용")

            if waste_types:
                evidences.append(
                    EvidenceCreate(
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                        data_source_id=data_source_id,
                        category=EvidenceCategory.WASTE,
                        indicator="폐기물_종류",
                        value=", ".join(waste_types),
                        numeric_value=None,
                        unit="",
                        observed_at=first_observed,
                        screening_only=screening_only,
                        metadata_json={
                            "region": first_region,
                            "date": first_date_str,
                            "source": "생활쓰레기배출정보 배출항목 파생",
                        },
                    )
                )

        logger.info(
            "생활쓰레기배출정보 정규화 완료: %d건 증거 생성", len(evidences)
        )
        return evidences

    @staticmethod
    def _parse_numeric(value: Any) -> float | None:
        """값을 수치로 변환한다."""
        if value is None:
            return None
        try:
            return float(str(value).strip().replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_items(raw_payload: dict[str, Any]) -> list[dict]:
        """다양한 응답 구조에서 항목 목록을 추출한다."""
        # 패턴 1: { data: [...] }
        data = raw_payload.get("data", [])
        if isinstance(data, list) and data:
            return data

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

        # 패턴 4: top-level list (일부 API)
        if isinstance(raw_payload.get("result"), list):
            return raw_payload["result"]

        return []
