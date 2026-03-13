"""환경기준별 법적 근거 매핑.

기존 env_standards.py의 각 기준값에 법적 근거 조문을 매핑한다.
각 환경 매체별로 근거 법령과 조문을 관리하며,
개별 지표 수준에서의 법적 근거 조회를 지원한다.

참조 법령:
- 환경정책기본법 시행령 별표 제1호 (대기환경기준, 수질환경기준, 소음환경기준)
- 토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalReference:
    """법적 근거 정보."""

    law_name: str       # 법률명 (예: "환경정책기본법 시행령")
    article: str        # 조문 (예: "별표 제1호")
    legal_basis: str    # 전체 법적 근거 문자열
    description: str    # 기준 분류 설명


# ────────────────────────────────────────────
# 매체별 법적 근거 (카테고리 수준)
# ────────────────────────────────────────────

AIR_LEGAL_REF = LegalReference(
    law_name="환경정책기본법 시행령",
    article="별표 제1호",
    legal_basis="환경정책기본법 시행령 별표 제1호 (대기환경기준)",
    description="대기환경기준",
)

WATER_LEGAL_REF = LegalReference(
    law_name="환경정책기본법 시행령",
    article="별표 제1호",
    legal_basis="환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준) — 하천 생활환경기준",
    description="수질 및 수생태계 환경기준 — 하천 생활환경기준",
)

NOISE_LEGAL_REF = LegalReference(
    law_name="환경정책기본법 시행령",
    article="별표 제1호",
    legal_basis="환경정책기본법 시행령 별표 제1호 (소음환경기준)",
    description="소음환경기준",
)

SOIL_LEGAL_REF = LegalReference(
    law_name="토양환경보전법 시행규칙",
    article="별표 제3호",
    legal_basis="토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)",
    description="토양오염우려기준",
)


# ────────────────────────────────────────────
# 카테고리 → 법적 근거 매핑
# ────────────────────────────────────────────

CATEGORY_LEGAL_REFS: dict[str, LegalReference] = {
    "air_quality": AIR_LEGAL_REF,
    "water_quality": WATER_LEGAL_REF,
    "noise_vibration": NOISE_LEGAL_REF,
    "soil": SOIL_LEGAL_REF,
}


# ────────────────────────────────────────────
# 지표별 법적 근거 매핑
# {indicator → {standard_value, legal_basis, law_name, article}}
# ────────────────────────────────────────────

@dataclass(frozen=True)
class IndicatorLegalInfo:
    """개별 지표의 법적 근거 정보."""

    indicator: str         # 지표명
    standard_value: float  # 기준값
    unit: str              # 단위
    legal_basis: str       # 법적 근거 전체 문자열
    law_name: str          # 법률명
    article: str           # 조문


# 대기환경기준 — 지표별 법적 근거
AIR_INDICATOR_REFS: dict[str, IndicatorLegalInfo] = {
    "PM10_연평균": IndicatorLegalInfo(
        "PM10_연평균", 50.0, "ug/m3",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "PM10_24시간": IndicatorLegalInfo(
        "PM10_24시간", 100.0, "ug/m3",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "PM2.5_연평균": IndicatorLegalInfo(
        "PM2.5_연평균", 15.0, "ug/m3",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "PM2.5_24시간": IndicatorLegalInfo(
        "PM2.5_24시간", 35.0, "ug/m3",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "SO2_연평균": IndicatorLegalInfo(
        "SO2_연평균", 0.02, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "SO2_24시간": IndicatorLegalInfo(
        "SO2_24시간", 0.05, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "SO2_1시간": IndicatorLegalInfo(
        "SO2_1시간", 0.15, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "NO2_연평균": IndicatorLegalInfo(
        "NO2_연평균", 0.03, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "NO2_24시간": IndicatorLegalInfo(
        "NO2_24시간", 0.06, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "NO2_1시간": IndicatorLegalInfo(
        "NO2_1시간", 0.10, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "CO_8시간": IndicatorLegalInfo(
        "CO_8시간", 9.0, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "CO_1시간": IndicatorLegalInfo(
        "CO_1시간", 25.0, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "CO_연평균": IndicatorLegalInfo(
        "CO_연평균", 9.0, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "O3_8시간": IndicatorLegalInfo(
        "O3_8시간", 0.06, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "O3_1시간": IndicatorLegalInfo(
        "O3_1시간", 0.1, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
    "O3_연평균": IndicatorLegalInfo(
        "O3_연평균", 0.06, "ppm",
        AIR_LEGAL_REF.legal_basis, AIR_LEGAL_REF.law_name, AIR_LEGAL_REF.article,
    ),
}

# 수질환경기준 — 지표별 법적 근거 (III등급 '보통' 기준)
WATER_INDICATOR_REFS: dict[str, IndicatorLegalInfo] = {
    "BOD": IndicatorLegalInfo(
        "BOD", 5.0, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
    "COD": IndicatorLegalInfo(
        "COD", 7.0, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
    "SS": IndicatorLegalInfo(
        "SS", 25.0, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
    "DO": IndicatorLegalInfo(
        "DO", 5.0, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
    "T-P": IndicatorLegalInfo(
        "T-P", 0.2, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
    "T-N": IndicatorLegalInfo(
        "T-N", 1.0, "mg/L",
        WATER_LEGAL_REF.legal_basis, WATER_LEGAL_REF.law_name, WATER_LEGAL_REF.article,
    ),
}

# 소음환경기준 — 지표별 법적 근거
NOISE_INDICATOR_REFS: dict[str, IndicatorLegalInfo] = {
    "소음_Leq_주간": IndicatorLegalInfo(
        "소음_Leq_주간", 55.0, "dB(A)",
        NOISE_LEGAL_REF.legal_basis, NOISE_LEGAL_REF.law_name, NOISE_LEGAL_REF.article,
    ),
    "소음_Leq_야간": IndicatorLegalInfo(
        "소음_Leq_야간", 45.0, "dB(A)",
        NOISE_LEGAL_REF.legal_basis, NOISE_LEGAL_REF.law_name, NOISE_LEGAL_REF.article,
    ),
}

# 토양오염우려기준 — 지표별 법적 근거 (1지역)
SOIL_INDICATOR_REFS: dict[str, IndicatorLegalInfo] = {
    "Cd": IndicatorLegalInfo(
        "Cd", 4.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
    "Cu": IndicatorLegalInfo(
        "Cu", 150.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
    "Pb": IndicatorLegalInfo(
        "Pb", 200.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
    "Zn": IndicatorLegalInfo(
        "Zn", 300.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
    "Ni": IndicatorLegalInfo(
        "Ni", 100.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
    "Cr6+": IndicatorLegalInfo(
        "Cr6+", 5.0, "mg/kg",
        SOIL_LEGAL_REF.legal_basis, SOIL_LEGAL_REF.law_name, SOIL_LEGAL_REF.article,
    ),
}


# ────────────────────────────────────────────
# 전체 지표 법적 근거 통합 매핑
# ────────────────────────────────────────────

ALL_INDICATOR_REFS: dict[str, IndicatorLegalInfo] = {
    **AIR_INDICATOR_REFS,
    **WATER_INDICATOR_REFS,
    **NOISE_INDICATOR_REFS,
    **SOIL_INDICATOR_REFS,
}


def get_legal_reference(indicator: str) -> IndicatorLegalInfo | None:
    """지표명으로 법적 근거를 조회한다."""
    return ALL_INDICATOR_REFS.get(indicator)


def get_category_legal_reference(category: str) -> LegalReference | None:
    """카테고리로 법적 근거를 조회한다."""
    return CATEGORY_LEGAL_REFS.get(category)
