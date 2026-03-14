"""국토교통부 토지이용규제정보서비스 커넥터.

토지이용규제정보서비스 API를 통해 지역지구별 행위제한 정보를 수집한다.
- 토지이용행위명 검색 (DTsearchLunCd)
- 행위제한 정보 조회 (DTarLandUseInfo)
- 공공데이터포털 인증키 기반 호출 (DATA_GO_KR_API_KEY)
- API 문서: https://www.data.go.kr/data/15058410/openapi.do
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx

from app.config import settings
from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCategory, EvidenceCreate

logger = logging.getLogger(__name__)

# 국토교통부 토지이용규제정보서비스 엔드포인트
LAND_REG_BASE_URL = (
    "https://apis.data.go.kr/1613000/arLandUseInfoService"
)

# 주요 용도지역 코드 매핑
UCODE_MAP = {
    "UQA100": "주거지역",
    "UQA110": "제1종전용주거지역",
    "UQA120": "제2종전용주거지역",
    "UQA130": "제1종일반주거지역",
    "UQA140": "제2종일반주거지역",
    "UQA150": "제3종일반주거지역",
    "UQA160": "준주거지역",
    "UQA200": "상업지역",
    "UQA210": "중심상업지역",
    "UQA220": "일반상업지역",
    "UQA230": "근린상업지역",
    "UQA240": "유통상업지역",
    "UQA300": "공업지역",
    "UQA310": "전용공업지역",
    "UQA320": "일반공업지역",
    "UQA330": "준공업지역",
    "UQA400": "녹지지역",
    "UQA410": "보전녹지지역",
    "UQA420": "생산녹지지역",
    "UQA430": "자연녹지지역",
}


class LandUseRegulationConnector(BaseConnector):
    """국토교통부 토지이용규제정보서비스 커넥터."""

    connector_key = "land_use_regulation"
    display_name = "국토교통부 토지이용규제정보"

    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """토지이용규제정보 API를 호출하여 행위제한 정보를 반환한다.

        params:
            area_cd: 시군구 코드 (예: "11680" = 서울 강남구) — 필수
            ucode: 용도지역 코드 (예: "UQA100" = 주거지역, 기본: "UQA100")

        Returns:
            행위제한 정보 딕셔너리
        """
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            raise ValueError(
                "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다."
            )

        area_cd = params.get("area_cd")
        if not area_cd:
            raise ValueError("area_cd(시군구 코드) 파라미터가 필요합니다.")

        # 다수 용도지역 코드에 대해 행위제한 조회
        ucodes = params.get("ucodes", ["UQA100"])
        if isinstance(ucodes, str):
            ucodes = [ucodes]

        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient(
            timeout=settings.CONNECTOR_TIMEOUT
        ) as client:
            # 행위명이 없으면 "건축"을 기본값으로 사용
            land_use_nm = params.get("land_use_nm", "건축")

            for ucode in ucodes:
                query_params = {
                    "serviceKey": api_key,
                    "areaCd": str(area_cd),
                    "ucodeList": ucode,
                    "landUseNm": land_use_nm,
                }

                url = f"{LAND_REG_BASE_URL}/DTarLandUseInfo"

                logger.info(
                    "토지이용규제 API 호출: 시군구=%s, 용도지역=%s(%s)",
                    area_cd, ucode,
                    UCODE_MAP.get(ucode, ucode),
                )

                try:
                    response = await client.get(url, params=query_params)
                    response.raise_for_status()

                    items = self._parse_xml_response(
                        response.content, ucode,
                    )
                    results.extend(items)
                except Exception as e:
                    logger.warning(
                        "토지이용규제 %s 조회 실패: %s", ucode, e,
                    )

        logger.info(
            "토지이용규제 API 응답: 총 %d건", len(results),
        )

        return {
            "area_cd": area_cd,
            "items": results,
            "total_count": len(results),
        }

    @staticmethod
    def _parse_xml_response(
        xml_bytes: bytes, ucode: str,
    ) -> list[dict[str, Any]]:
        """XML 응답을 파싱하여 행위제한 항목 목록으로 변환한다."""
        items: list[dict[str, Any]] = []
        try:
            # EUC-KR 인코딩 처리
            try:
                xml_text = xml_bytes.decode("euc-kr")
            except UnicodeDecodeError:
                xml_text = xml_bytes.decode("utf-8", errors="replace")

            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            logger.warning("토지이용규제 XML 파싱 실패: %s", e)
            return items

        # 에러 응답 확인 (ERROR_CODE 태그)
        error_code = root.findtext("ERROR_CODE")
        if error_code:
            error_msg = root.findtext("ERROR_MSG", "")
            logger.warning(
                "토지이용규제 API 오류: [%s] %s", error_code, error_msg,
            )
            return items

        # 정상 응답: header.resultCode 확인
        result_code = ""
        header = root.find(".//header")
        if header is not None:
            rc = header.find("resultCode")
            if rc is not None and rc.text:
                result_code = rc.text.strip()

        if result_code not in ("0", ""):
            return items

        for item_el in root.findall(".//item"):
            item: dict[str, Any] = {"ucode": ucode}
            for child in item_el:
                tag = child.tag
                text = (child.text or "").strip()
                item[tag] = text

            # actRegList/luInfoList 내 행위제한 추출
            for lu_info in item_el.findall(".//luInfoList"):
                desc_el = lu_info.find("NODE_DESC")
                law_el = lu_info.find("LU_REF_LAW_NM1")
                if desc_el is not None and desc_el.text:
                    item.setdefault("restrictions", []).append({
                        "description": desc_el.text.strip(),
                        "law_ref": (
                            law_el.text.strip()
                            if law_el is not None and law_el.text
                            else ""
                        ),
                    })

            items.append(item)

        return items

    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """토지이용규제 응답을 EvidenceCreate 목록으로 변환한다."""
        evidences: list[EvidenceCreate] = []

        items = raw_payload.get("items", [])
        area_cd = raw_payload.get("area_cd", "")
        now = datetime.now(tz=timezone.utc)

        if not items:
            logger.warning("토지이용규제 응답에 행위제한 데이터가 없습니다.")
            return evidences

        for item in items:
            ucode = item.get("ucode", "")
            uname = item.get("UNAME", UCODE_MAP.get(ucode, ucode))
            law_ref = item.get("UCODE_REF_LAW_NM", "")
            restrictions = item.get("restrictions", [])

            # 용도지역명 + 법적 근거
            evidences.append(
                EvidenceCreate(
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    data_source_id=data_source_id,
                    category=EvidenceCategory.LAND_USE,
                    indicator="행위제한_용도지역",
                    value=uname,
                    unit=None,
                    observed_at=now,
                    screening_only=screening_only,
                    metadata_json={
                        "source": "토지이용규제정보서비스",
                        "area_cd": area_cd,
                        "ucode": ucode,
                        "law_ref": law_ref,
                    },
                )
            )

            # 행위제한 내용
            for restriction in restrictions:
                desc = restriction.get("description", "")
                if desc:
                    evidences.append(
                        EvidenceCreate(
                            project_id=project_id,
                            snapshot_id=snapshot_id,
                            data_source_id=data_source_id,
                            category=EvidenceCategory.LAND_USE,
                            indicator="행위제한_내용",
                            value=desc,
                            unit=None,
                            observed_at=now,
                            screening_only=screening_only,
                            metadata_json={
                                "source": "토지이용규제정보서비스",
                                "ucode": ucode,
                                "uname": uname,
                                "law_ref": restriction.get("law_ref", ""),
                            },
                        )
                    )

        logger.info(
            "토지이용규제 정규화 완료: %d건 증거 생성", len(evidences),
        )
        return evidences
