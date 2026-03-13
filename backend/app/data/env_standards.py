"""한국 환경기준 데이터.

환경정책기본법 시행령 별표에 정의된 환경기준을 딕셔너리 구조로 관리한다.
각 기준은 지표명 → 시간기준 → 기준값 형태로 정의된다.

참조 법령:
- 대기환경기준: 환경정책기본법 시행령 별표 제1호 (대기환경기준)
- 수질환경기준: 환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준 — 하천 생활환경기준)
- 소음환경기준: 환경정책기본법 시행령 별표 제1호 (소음환경기준)
- 토양오염우려기준: 토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComparisonOp(str, Enum):
    """기준값 비교 방향."""

    LEQ = "leq"  # 이하 (측정값 ≤ 기준값이면 적합)
    GEQ = "geq"  # 이상 (측정값 ≥ 기준값이면 적합)


@dataclass(frozen=True)
class Standard:
    """단일 환경기준 항목."""

    indicator: str         # 지표명 (evidence.indicator와 매칭)
    time_basis: str        # 시간기준 (연평균, 24시간, 1시간, 8시간, 주간, 야간 등)
    limit_value: float     # 기준값
    unit: str              # 단위
    op: ComparisonOp       # 비교 방향
    description: str = ""  # 설명
    legal_basis: str = ""  # 법적 근거 (예: "환경정책기본법 시행령 별표 제1호")


# ────────────────────────────────────────────
# 대기환경기준 (환경정책기본법 시행령 별표 제1호)
# ────────────────────────────────────────────

_AIR_LEGAL = "환경정책기본법 시행령 별표 제1호 (대기환경기준)"

AIR_STANDARDS: list[Standard] = [
    # PM10
    Standard("PM10_연평균", "연평균", 50.0, "ug/m3", ComparisonOp.LEQ, "미세먼지 연평균", _AIR_LEGAL),
    Standard("PM10_24시간", "24시간", 100.0, "ug/m3", ComparisonOp.LEQ, "미세먼지 24시간 평균", _AIR_LEGAL),
    # PM2.5
    Standard("PM2.5_연평균", "연평균", 15.0, "ug/m3", ComparisonOp.LEQ, "초미세먼지 연평균", _AIR_LEGAL),
    Standard("PM2.5_24시간", "24시간", 35.0, "ug/m3", ComparisonOp.LEQ, "초미세먼지 24시간 평균", _AIR_LEGAL),
    # SO2
    Standard("SO2_연평균", "연평균", 0.02, "ppm", ComparisonOp.LEQ, "아황산가스 연평균", _AIR_LEGAL),
    Standard("SO2_24시간", "24시간", 0.05, "ppm", ComparisonOp.LEQ, "아황산가스 24시간 평균", _AIR_LEGAL),
    Standard("SO2_1시간", "1시간", 0.15, "ppm", ComparisonOp.LEQ, "아황산가스 1시간 평균", _AIR_LEGAL),
    # NO2
    Standard("NO2_연평균", "연평균", 0.03, "ppm", ComparisonOp.LEQ, "이산화질소 연평균", _AIR_LEGAL),
    Standard("NO2_24시간", "24시간", 0.06, "ppm", ComparisonOp.LEQ, "이산화질소 24시간 평균", _AIR_LEGAL),
    Standard("NO2_1시간", "1시간", 0.10, "ppm", ComparisonOp.LEQ, "이산화질소 1시간 평균", _AIR_LEGAL),
    # CO
    Standard("CO_8시간", "8시간", 9.0, "ppm", ComparisonOp.LEQ, "일산화탄소 8시간 평균", _AIR_LEGAL),
    Standard("CO_1시간", "1시간", 25.0, "ppm", ComparisonOp.LEQ, "일산화탄소 1시간 평균", _AIR_LEGAL),
    Standard("CO_연평균", "연평균", 9.0, "ppm", ComparisonOp.LEQ, "일산화탄소 (8시간 기준 적용)", _AIR_LEGAL),
    # O3
    Standard("O3_8시간", "8시간", 0.06, "ppm", ComparisonOp.LEQ, "오존 8시간 평균", _AIR_LEGAL),
    Standard("O3_1시간", "1시간", 0.1, "ppm", ComparisonOp.LEQ, "오존 1시간 평균", _AIR_LEGAL),
    Standard("O3_연평균", "연평균", 0.06, "ppm", ComparisonOp.LEQ, "오존 (8시간 기준 적용)", _AIR_LEGAL),
]

# 대기 지표 → 기준 빠른 조회 (indicator → list of Standard)
_AIR_STANDARDS_MAP: dict[str, list[Standard]] = {}
for _s in AIR_STANDARDS:
    _AIR_STANDARDS_MAP.setdefault(_s.indicator, []).append(_s)


# ────────────────────────────────────────────
# 수질환경기준 — 하천 생활환경기준
# ────────────────────────────────────────────

@dataclass(frozen=True)
class WaterGrade:
    """하천 수질등급 기준."""

    grade: str        # 등급 코드 (Ia, Ib, II, III, IV, V)
    grade_name: str   # 등급명 (매우 좋음, 좋음, ...)
    bod: float        # BOD 상한 (mg/L)
    cod: float        # COD 상한 (mg/L)
    ss: float         # SS 상한 (mg/L)
    do_min: float     # DO 하한 (mg/L)
    tp: float         # T-P 상한 (mg/L)


WATER_GRADES: list[WaterGrade] = [
    WaterGrade("Ia", "매우 좋음", 1.0, 2.0, 25.0, 7.5, 0.02),
    WaterGrade("Ib", "좋음", 2.0, 4.0, 25.0, 5.0, 0.04),
    WaterGrade("II", "약간 좋음", 3.0, 5.0, 25.0, 5.0, 0.1),
    WaterGrade("III", "보통", 5.0, 7.0, 25.0, 5.0, 0.2),
    WaterGrade("IV", "약간 나쁨", 8.0, 9.0, 100.0, 2.0, 0.3),
    WaterGrade("V", "나쁨", 10.0, 11.0, None, 2.0, 0.5),  # type: ignore[arg-type]
]

# 수질 지표별 환경기준 (하천 III등급 '보통' 기준을 기본 비교 기준으로 사용)
# 실무에서 III등급은 일반적 하천의 기본 환경기준으로 가장 많이 참조됨
_WATER_LEGAL = "환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준) — 하천 생활환경기준"

WATER_STANDARDS: list[Standard] = [
    Standard("BOD", "평균", 5.0, "mg/L", ComparisonOp.LEQ, "생물화학적산소요구량 (III등급 기준)", _WATER_LEGAL),
    Standard("COD", "평균", 7.0, "mg/L", ComparisonOp.LEQ, "화학적산소요구량 (III등급 기준)", _WATER_LEGAL),
    Standard("SS", "평균", 25.0, "mg/L", ComparisonOp.LEQ, "부유물질 (III등급 기준)", _WATER_LEGAL),
    Standard("DO", "평균", 5.0, "mg/L", ComparisonOp.GEQ, "용존산소 (III등급 기준)", _WATER_LEGAL),
    Standard("T-P", "평균", 0.2, "mg/L", ComparisonOp.LEQ, "총인 (III등급 기준)", _WATER_LEGAL),
    Standard("T-N", "평균", 1.0, "mg/L", ComparisonOp.LEQ, "총질소 (참고기준)", _WATER_LEGAL),
]


# ────────────────────────────────────────────
# 소음환경기준 (지역구분 "나" 일반지역 기준 — 기본 비교용)
# 지역구분별 차등 기준은 regulations/area_classifications.py 참조
# ────────────────────────────────────────────

_NOISE_LEGAL = "환경정책기본법 시행령 별표 제1호 (소음환경기준)"

NOISE_STANDARDS: list[Standard] = [
    Standard("소음_Leq_주간", "주간(06~22시)", 55.0, "dB(A)", ComparisonOp.LEQ,
             "소음 환경기준 주거지역 주간", _NOISE_LEGAL),
    Standard("소음_Leq_야간", "야간(22~06시)", 45.0, "dB(A)", ComparisonOp.LEQ,
             "소음 환경기준 주거지역 야간", _NOISE_LEGAL),
]


# ────────────────────────────────────────────
# 토양오염 우려기준 (토양환경보전법 시행규칙 별표 3, 1지역)
# ────────────────────────────────────────────

_SOIL_LEGAL = "토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)"

SOIL_STANDARDS: list[Standard] = [
    Standard("Cd", "우려기준", 4.0, "mg/kg", ComparisonOp.LEQ, "카드뮴 1지역 우려기준", _SOIL_LEGAL),
    Standard("Cu", "우려기준", 150.0, "mg/kg", ComparisonOp.LEQ, "구리 1지역 우려기준", _SOIL_LEGAL),
    Standard("Pb", "우려기준", 200.0, "mg/kg", ComparisonOp.LEQ, "납 1지역 우려기준", _SOIL_LEGAL),
    Standard("Zn", "우려기준", 300.0, "mg/kg", ComparisonOp.LEQ, "아연 1지역 우려기준", _SOIL_LEGAL),
    Standard("Ni", "우려기준", 100.0, "mg/kg", ComparisonOp.LEQ, "니켈 1지역 우려기준", _SOIL_LEGAL),
    Standard("Cr6+", "우려기준", 5.0, "mg/kg", ComparisonOp.LEQ, "6가크롬 1지역 우려기준", _SOIL_LEGAL),
]


# ────────────────────────────────────────────
# 카테고리별 기준 매핑
# ────────────────────────────────────────────

# evidence 카테고리 → 해당 환경기준 목록
STANDARDS_BY_CATEGORY: dict[str, list[Standard]] = {
    "air_quality": AIR_STANDARDS,
    "water_quality": WATER_STANDARDS,
    "noise_vibration": NOISE_STANDARDS,
    "soil": SOIL_STANDARDS,
}


def get_standards_for_category(category: str) -> list[Standard]:
    """카테고리에 해당하는 환경기준 목록을 반환한다."""
    return STANDARDS_BY_CATEGORY.get(category, [])


def get_standard_for_indicator(
    category: str,
    indicator: str,
) -> Standard | None:
    """카테고리와 지표명으로 단일 환경기준을 조회한다.

    동일 지표에 여러 시간기준이 있으면 첫 번째(주기준)를 반환한다.
    """
    standards = get_standards_for_category(category)
    for s in standards:
        if s.indicator == indicator:
            return s
    return None


def determine_water_grade(
    bod: float | None = None,
    cod: float | None = None,
    do_val: float | None = None,
    tp: float | None = None,
) -> WaterGrade | None:
    """수질 측정값으로 하천 생활환경기준 등급을 판정한다.

    BOD 기준으로 우선 판정하며, 다른 항목은 보조 판단에 사용한다.
    가장 나쁜(높은) 등급을 반환한다.
    """
    if bod is None and cod is None:
        return None

    worst_idx = 0  # 최상위 등급부터 시작

    for i, grade in enumerate(WATER_GRADES):
        # BOD 기준
        if bod is not None and bod > grade.bod:
            worst_idx = max(worst_idx, i + 1)
        # COD 기준
        if cod is not None and cod > grade.cod:
            worst_idx = max(worst_idx, i + 1)
        # DO 기준 (하한)
        if do_val is not None and do_val < grade.do_min:
            worst_idx = max(worst_idx, i + 1)
        # T-P 기준
        if tp is not None and tp > grade.tp:
            worst_idx = max(worst_idx, i + 1)

    # 범위 보정 (V등급 초과 시 V등급으로)
    worst_idx = min(worst_idx, len(WATER_GRADES) - 1)
    return WATER_GRADES[worst_idx]
