"""지역구분별 환경기준 차등.

소음환경기준은 지역구분에 따라 기준값이 달라진다.
대기·수질은 전국 동일 기준이므로 지역구분을 적용하지 않는다.

참조 법령:
- 환경정책기본법 시행령 별표 제1호 (소음환경기준)
- 지역구분은 국토의 계획 및 이용에 관한 법률에 의한 용도지역 기준
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseStandardByArea:
    """소음 지역구분별 기준값."""

    area_code: str          # 지역 코드 ("가", "나", "다", "라")
    area_name: str          # 지역 설명
    applicable_zones: str   # 해당 용도지역
    # 일반지역 기준
    daytime_general: float  # 주간(06~22시) 일반지역 dB(A)
    nighttime_general: float  # 야간(22~06시) 일반지역 dB(A)
    # 도로변지역 기준
    daytime_roadside: float  # 주간(06~22시) 도로변 dB(A)
    nighttime_roadside: float  # 야간(22~06시) 도로변 dB(A)


# ────────────────────────────────────────────
# 소음환경기준 지역구분
# 환경정책기본법 시행령 별표 제1호 (소음환경기준) 기준
# ────────────────────────────────────────────

NOISE_AREA_STANDARDS: dict[str, NoiseStandardByArea] = {
    "가": NoiseStandardByArea(
        area_code="가",
        area_name="\"가\" 지역",
        applicable_zones="주거지역, 녹지지역, 관리지역 중 취락지구·주거개발진흥지구, 자연환경보전지역",
        daytime_general=50.0,
        nighttime_general=40.0,
        daytime_roadside=55.0,
        nighttime_roadside=45.0,
    ),
    "나": NoiseStandardByArea(
        area_code="나",
        area_name="\"나\" 지역",
        applicable_zones="상업지역, 준주거지역",
        daytime_general=55.0,
        nighttime_general=45.0,
        daytime_roadside=60.0,
        nighttime_roadside=50.0,
    ),
    "다": NoiseStandardByArea(
        area_code="다",
        area_name="\"다\" 지역",
        applicable_zones="공업지역 (전용공업지역 제외)",
        daytime_general=60.0,
        nighttime_general=50.0,
        daytime_roadside=65.0,
        nighttime_roadside=55.0,
    ),
    "라": NoiseStandardByArea(
        area_code="라",
        area_name="\"라\" 지역",
        applicable_zones="전용공업지역",
        daytime_general=65.0,
        nighttime_general=55.0,
        daytime_roadside=70.0,
        nighttime_roadside=60.0,
    ),
}

# 일반지역 기준 딕셔너리 (간편 조회용)
# {area_code → {time_period → standard_value}}
NOISE_AREA_GENERAL: dict[str, dict[str, float]] = {
    code: {
        "주간": std.daytime_general,
        "야간": std.nighttime_general,
    }
    for code, std in NOISE_AREA_STANDARDS.items()
}

# 도로변지역 기준 딕셔너리 (간편 조회용)
NOISE_AREA_ROADSIDE: dict[str, dict[str, float]] = {
    code: {
        "주간": std.daytime_roadside,
        "야간": std.nighttime_roadside,
    }
    for code, std in NOISE_AREA_STANDARDS.items()
}


def get_noise_standard(
    area_code: str,
    time_period: str,
    is_roadside: bool = False,
) -> float | None:
    """지역구분 + 시간대 + 도로변 여부로 소음 기준값을 조회한다.

    Args:
        area_code: 지역 코드 ("가", "나", "다", "라")
        time_period: 시간대 ("주간" 또는 "야간")
        is_roadside: 도로변지역 여부 (기본: False → 일반지역)

    Returns:
        기준값 dB(A) 또는 None (미등록 지역/시간대)
    """
    area_dict = NOISE_AREA_ROADSIDE if is_roadside else NOISE_AREA_GENERAL
    area = area_dict.get(area_code)
    if area is None:
        return None
    return area.get(time_period)


def get_noise_area_info(area_code: str) -> NoiseStandardByArea | None:
    """지역구분 코드로 소음 기준 전체 정보를 조회한다."""
    return NOISE_AREA_STANDARDS.get(area_code)
