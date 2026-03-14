"""섹션별 서술문 템플릿 엔진.

Post-1 통계 + Post-2 기준비교 결과를 입력으로 받아
환경영향평가서 초안의 섹션별 서술문을 결정적(deterministic) 방식으로 생성한다.
LLM을 사용하지 않으며, 모든 서술은 수집된 증거 데이터에 기반한다.

Reg-2: 환경기준 비교 서술 시 법적 근거를 자동 삽입한다.
Pred-3: 예측 모델 결과를 기반으로 영향 예측 서술문을 생성한다.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.data.env_standards import WATER_GRADES
from app.services.section_planner import SectionDefinition
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
)
from app.services.statistics import IndicatorStats, SectionStats, TextIndicatorInfo

if TYPE_CHECKING:
    from app.services.prediction.base import PredictionItem, PredictionResult

# ────────────────────────────────────────────
# 섹션별 법적 근거 서술문 접두어
# ────────────────────────────────────────────

_AIR_LEGAL_PREFIX = "환경정책기본법 시행령 별표 제1호에 따른 대기환경기준"
_WATER_LEGAL_PREFIX = "환경정책기본법 시행령 별표 제1호에 따른 하천 수질 및 수생태계 생활환경기준"
_NOISE_LEGAL_PREFIX = "환경정책기본법 시행령 별표 제1호에 따른 소음환경기준"

# 법적 근거 문자열 → 서술문용 텍스트 변환 매핑
_LEGAL_REF_NARRATIVE: dict[str, str] = {
    "환경정책기본법 시행령 별표 제1호 (대기환경기준)":
        _AIR_LEGAL_PREFIX,
    "환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준) — 하천 생활환경기준":
        _WATER_LEGAL_PREFIX,
    "환경정책기본법 시행령 별표 제1호 (소음환경기준)":
        _NOISE_LEGAL_PREFIX,
    "토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)":
        "토양환경보전법 시행규칙 별표 제3호에 따른 토양오염우려기준",
}


def _fmt(value: float | None, precision: int = 2) -> str:
    """수치를 적절한 자릿수로 포맷팅한다."""
    if value is None:
        return "-"
    # 정수에 가까우면 정수로 표시
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.{precision}f}"


def _period_str(stats: SectionStats) -> str:
    """통계의 관측 기간 문자열을 생성한다."""
    starts = [s.period_start for s in stats.indicator_stats if s.period_start]
    ends = [s.period_end for s in stats.indicator_stats if s.period_end]
    if not starts or not ends:
        return "수집 기간"
    s = min(starts)[:10]
    e = max(ends)[:10]
    return f"{s}~{e}" if s != e else s


def _status_text(status: str) -> str:
    """판정 상태를 한글로 변환한다."""
    if status == CheckStatus.PASS:
        return "이내"
    elif status == CheckStatus.FAIL:
        return "초과"
    return "-"


def _format_legal_ref(legal_basis: str) -> str:
    """법적 근거를 서술문에 삽입 가능한 형태로 변환한다."""
    if not legal_basis:
        return "환경기준"
    return _LEGAL_REF_NARRATIVE.get(legal_basis, legal_basis)


def _get_water_grade_bod(grade: str) -> float | None:
    """수질등급 코드로 BOD 상한값을 조회한다."""
    for wg in WATER_GRADES:
        if wg.grade == grade:
            return wg.bod
    return None


def _extract_area_from_description(description: str) -> str:
    """기준 설명에서 지역구분을 추출한다 (예: '1지역')."""
    m = re.search(r"(\d+지역)", description)
    return m.group(1) if m else ""


# ────────────────────────────────────────────
# 대기질 서술문
# ────────────────────────────────────────────

def generate_air_quality_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """대기질 섹션 서술문을 생성한다."""
    if section_stats.total_numeric_count == 0:
        return _no_data_narrative()

    period = _period_str(section_stats)
    total = section_stats.total_numeric_count

    lines: list[str] = []

    # 도입부
    lines.append(
        f"본 사업지역 인근의 대기질 현황을 분석한 결과, "
        f"{period} 동안 총 {total}건의 측정 데이터를 수집하였다."
    )

    # 지표별 서술 (PM10, PM2.5 우선, 나머지 순서대로)
    priority_order = ["PM10_연평균", "PM2.5_연평균", "NO2_연평균",
                      "SO2_연평균", "CO_연평균", "O3_연평균"]
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    check_map: dict[str, IndicatorCheckResult] = {}
    if section_check:
        check_map = {r.indicator: r for r in section_check.indicators}

    for indicator in priority_order:
        stat = stats_map.get(indicator)
        if stat is None or stat.count == 0:
            continue

        unit = stat.unit or "ug/m3"
        avg = _fmt(stat.mean)
        cr = check_map.get(indicator)

        if cr and cr.standard_value is not None:
            std_val = _fmt(cr.standard_value)
            status = _status_text(cr.status)
            time_basis = cr.time_basis or "연평균"
            lines.append(
                f"{indicator} 평균 {avg} {unit}으로 "
                f"{_AIR_LEGAL_PREFIX}({time_basis} {std_val} {unit}) {status} 수준이다."
            )
        else:
            lines.append(f"{indicator} 평균 {avg} {unit}이다.")

    # 종합 판정
    if section_check:
        fail_indicators = [
            r.indicator for r in section_check.indicators
            if r.status == CheckStatus.FAIL
        ]
        if fail_indicators:
            names = ", ".join(fail_indicators)
            lines.append(
                f"{names}의 경우 환경기준을 초과하는 것으로 나타나 "
                f"사업 시행 시 저감대책 수립이 필요하다."
            )
        else:
            measured = [r for r in section_check.indicators if r.status != CheckStatus.NA]
            if measured:
                lines.append("전반적으로 대기환경기준을 만족하는 것으로 나타났다.")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 수질 서술문
# ────────────────────────────────────────────

def generate_water_quality_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """수질 섹션 서술문을 생성한다."""
    if section_stats.total_numeric_count == 0:
        return _no_data_narrative()

    period = _period_str(section_stats)
    total = section_stats.total_numeric_count

    lines: list[str] = []

    # 도입부
    lines.append(
        f"본 사업지역 인근 수질측정지점의 수질 현황을 분석한 결과, "
        f"{period} 동안 총 {total}건의 측정 데이터를 수집하였다."
    )

    # 주요 지표 서술 (BOD, COD 우선)
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    check_map: dict[str, IndicatorCheckResult] = {}
    if section_check:
        check_map = {r.indicator: r for r in section_check.indicators}

    # BOD, COD 병합 서술
    bod_stat = stats_map.get("BOD")
    cod_stat = stats_map.get("COD")

    if bod_stat and cod_stat and bod_stat.count > 0 and cod_stat.count > 0:
        bod_avg = _fmt(bod_stat.mean)
        cod_avg = _fmt(cod_stat.mean)
        unit = bod_stat.unit or "mg/L"

        # 등급 정보
        if section_check and section_check.water_grade:
            grade = section_check.water_grade
            grade_name = section_check.water_grade_name or ""
            # BOD 등급 기준값 조회
            grade_bod = _get_water_grade_bod(grade)
            grade_detail = f", BOD {_fmt(grade_bod)} {unit} 이하" if grade_bod else ""
            lines.append(
                f"BOD 평균 {bod_avg} {unit}, COD 평균 {cod_avg} {unit}로 "
                f"{_WATER_LEGAL_PREFIX} {grade}등급"
                f"({grade_name}{grade_detail}) 수준에 해당한다."
            )
        else:
            lines.append(
                f"BOD 평균 {bod_avg} {unit}, COD 평균 {cod_avg} {unit}로 측정되었다."
            )

    # 기타 지표 서술
    other_indicators = ["SS", "DO", "T-N", "T-P"]
    indicator_parts: list[str] = []
    for ind in other_indicators:
        stat = stats_map.get(ind)
        if stat and stat.count > 0:
            unit = stat.unit or "mg/L"
            avg = _fmt(stat.mean)
            indicator_parts.append(f"{ind} {avg} {unit}")

    if indicator_parts:
        lines.append(", ".join(indicator_parts) + "로 측정되었다.")

    # 초과 지표 서술
    if section_check:
        fail_indicators = [
            r.indicator for r in section_check.indicators
            if r.status == CheckStatus.FAIL
        ]
        if fail_indicators:
            names = ", ".join(fail_indicators)
            lines.append(
                f"{names}이(가) 환경기준을 초과하여 수질 관리 대책 수립이 필요하다."
            )
        else:
            measured = [r for r in section_check.indicators if r.status != CheckStatus.NA]
            if measured:
                lines.append("전반적으로 수질환경기준을 만족하는 것으로 나타났다.")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 소음·진동 서술문
# ────────────────────────────────────────────

def generate_noise_vibration_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """소음·진동 섹션 서술문을 생성한다."""
    if section_stats.total_numeric_count == 0:
        return _no_data_narrative()

    lines: list[str] = []
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    check_map: dict[str, IndicatorCheckResult] = {}
    if section_check:
        check_map = {r.indicator: r for r in section_check.indicators}

    # 도입부
    parts: list[str] = []
    for ind_key, label in [("소음_Leq_주간", "주간 소음도"), ("소음_Leq_야간", "야간 소음도")]:
        stat = stats_map.get(ind_key)
        if stat and stat.count > 0:
            unit = stat.unit or "dB(A)"
            avg = _fmt(stat.mean)
            parts.append(f"{label} {avg} {unit}")

    if parts:
        lines.append(
            f"본 사업지역의 소음 현황을 조사한 결과, "
            + ", ".join(parts) + "로 측정되었다."
        )
    else:
        lines.append("본 사업지역의 소음 현황을 조사하였다.")

    # 판정 서술 (법적 근거 포함)
    if section_check:
        for ind_key, label in [("소음_Leq_주간", "주간"), ("소음_Leq_야간", "야간")]:
            cr = check_map.get(ind_key)
            if cr and cr.status != CheckStatus.NA and cr.standard_value is not None:
                std_val = _fmt(cr.standard_value)
                unit = cr.standard_unit or "dB(A)"
                if cr.status == CheckStatus.PASS:
                    lines.append(
                        f'{label} 소음은 {_NOISE_LEGAL_PREFIX}'
                        f'(일반지역 "나" {label} {std_val} {unit}) 이내로 적합하다.'
                    )
                elif cr.status == CheckStatus.FAIL:
                    lines.append(
                        f'{label} 소음은 {_NOISE_LEGAL_PREFIX}'
                        f'(일반지역 "나" {label} {std_val} {unit})을 초과하므로 '
                        f'방음대책 수립이 필요하다.'
                    )

    # 진동 서술
    vib_stat = stats_map.get("진동_Lv_주간")
    if vib_stat and vib_stat.count > 0:
        unit = vib_stat.unit or "dB(V)"
        avg = _fmt(vib_stat.mean)
        lines.append(f"진동은 주간 {avg} {unit}로 측정되었다.")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 생태 서술문
# ────────────────────────────────────────────

def generate_ecology_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """생태 섹션 서술문을 생성한다."""
    if section_stats.total_numeric_count == 0:
        # 비수치 데이터 (종수 등)도 없으면 미수집
        return _no_data_narrative()

    lines: list[str] = []
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}

    # 도입부
    parts: list[str] = []
    flora = stats_map.get("식물상_종수")
    fauna = stats_map.get("동물상_종수")

    if flora and flora.count > 0:
        parts.append(f"식물상 {_fmt(flora.mean, 0)}종")
    if fauna and fauna.count > 0:
        parts.append(f"동물상 {_fmt(fauna.mean, 0)}종")

    if parts:
        lines.append(
            f"본 사업지역의 생태 현황 조사 결과, "
            + ", ".join(parts) + "이 확인되었다."
        )
    else:
        lines.append("본 사업지역의 생태 현황 조사를 실시하였다.")

    # 녹지자연도
    nci = stats_map.get("녹지자연도")
    if nci and nci.count > 0:
        lines.append(f"녹지자연도는 {_fmt(nci.mean, 0)}등급이다.")

    # 법정보호종
    protected = stats_map.get("법정보호종")
    if protected and protected.count > 0:
        count = _fmt(protected.mean, 0)
        if protected.mean is not None and protected.mean > 0:
            lines.append(
                f"법정보호종은 {count}종이 확인되어 보호 대책 수립이 필요하다."
            )
        else:
            lines.append("법정보호종은 확인되지 않았다.")
    else:
        lines.append("법정보호종 조사 자료가 수집되지 않았다.")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 토지이용 서술문
# ────────────────────────────────────────────

def generate_land_use_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """토지이용 섹션 서술문을 생성한다.

    토지이용은 비수치형 데이터(지목, 용도지역구분, 용도지구)가 주를 이루므로
    텍스트 기반 서술문을 생성한다.
    """
    if not _has_any_data(section_stats):
        return _no_data_narrative()

    text_map = _text_indicator_map(section_stats)
    lines: list[str] = []

    # 지목, 용도지역구분을 기반으로 도입부 구성
    jmok = text_map.get("지목")
    yongdo = text_map.get("용도지역구분")
    yongdo_jigu = text_map.get("용도지구")

    intro_parts: list[str] = []
    if jmok:
        intro_parts.append(f"지목은 {jmok}이며")
    if yongdo:
        intro_parts.append(f"용도지역은 {yongdo}으로 지정되어 있다")

    if intro_parts:
        lines.append(
            "본 사업지역의 토지이용 현황을 조사한 결과, "
            + ", ".join(intro_parts) + "."
        )
    else:
        lines.append("본 사업지역의 토지이용 현황을 조사하였다.")

    if yongdo_jigu:
        lines.append(f"용도지구는 {yongdo_jigu}이다.")

    # 수치형 지표가 있으면 추가 서술
    for stat in section_stats.indicator_stats:
        if stat.count == 0:
            continue
        unit = f" {stat.unit}" if stat.unit else ""
        avg = _fmt(stat.mean)
        lines.append(f"{stat.indicator} 평균 {avg}{unit}로 조사되었다.")

    # text_map에 포함되지 않은 기타 텍스트 지표 서술
    known_text = {"지목", "용도지역구분", "용도지구"}
    for ti in section_stats.text_indicators:
        if ti.indicator not in known_text:
            values_str = ", ".join(ti.values[:5])
            lines.append(f"{ti.indicator}: {values_str}")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 문화재 서술문
# ────────────────────────────────────────────

def generate_cultural_heritage_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """문화재 섹션 서술문을 생성한다.

    문화재명은 비수치형, 이격거리는 수치형으로 혼합된 데이터를 처리한다.
    """
    if not _has_any_data(section_stats):
        return _no_data_narrative()

    text_map = _text_indicator_map(section_stats)
    lines: list[str] = []

    heritage_name = text_map.get("문화재명")
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    distance_stat = stats_map.get("이격거리")

    if heritage_name:
        intro = f"본 사업지역 인근의 문화재 현황을 조사한 결과, {heritage_name}이(가) 확인되었다."
        lines.append(intro)
    else:
        lines.append("본 사업지역 인근의 문화재 현황을 조사하였다.")

    if distance_stat and distance_stat.count > 0:
        unit = distance_stat.unit or "m"
        avg = _fmt(distance_stat.mean, 0)
        lines.append(f"사업지역과의 이격거리는 약 {avg} {unit}이다.")

    # 기타 텍스트 지표 (종별, 소재지 등)
    known_text = {"문화재명"}
    for ti in section_stats.text_indicators:
        if ti.indicator not in known_text and ti.values:
            values_str = ", ".join(ti.values[:5])
            lines.append(f"{ti.indicator}: {values_str}")

    # 기타 수치 지표
    for stat in section_stats.indicator_stats:
        if stat.indicator == "이격거리" or stat.count == 0:
            continue
        unit = f" {stat.unit}" if stat.unit else ""
        avg = _fmt(stat.mean)
        lines.append(f"{stat.indicator} 평균 {avg}{unit}로 조사되었다.")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 교통 서술문
# ────────────────────────────────────────────

def generate_traffic_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """교통 섹션 서술문을 생성한다.

    교통량(AADT), 도로명, 도로등급 등 혼합 데이터를 처리한다.
    """
    if not _has_any_data(section_stats):
        return _no_data_narrative("traffic")

    text_map = _text_indicator_map(section_stats)
    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    lines: list[str] = []

    # 도입부
    road_names = text_map.get("도로명")
    traffic_stat = stats_map.get("교통량_현황")

    if traffic_stat and traffic_stat.count > 0:
        unit = traffic_stat.unit or "대/일"
        avg = _fmt(traffic_stat.mean, 0)
        if road_names:
            lines.append(
                f"본 사업지역 인근 주요 도로({road_names})의 교통량 현황을 조사한 결과, "
                f"연평균일교통량(AADT)은 평균 {avg} {unit}으로 조사되었다."
            )
        else:
            lines.append(
                f"본 사업지역 인근의 교통량 현황을 조사한 결과, "
                f"연평균일교통량(AADT)은 평균 {avg} {unit}으로 조사되었다."
            )

        # 최대/최소 정보
        if traffic_stat.max is not None and traffic_stat.min is not None:
            lines.append(
                f"조사 구간 내 교통량은 최소 {_fmt(traffic_stat.min, 0)} {unit}에서 "
                f"최대 {_fmt(traffic_stat.max, 0)} {unit}의 범위이다."
            )
    else:
        lines.append("본 사업지역 인근의 교통량 현황을 조사하였다.")

    # 도로등급
    road_grade = text_map.get("도로등급")
    if road_grade:
        lines.append(f"조사 대상 도로의 등급은 {road_grade}이다.")

    # 기타 수치 지표
    for stat in section_stats.indicator_stats:
        if stat.indicator == "교통량_현황" or stat.count == 0:
            continue
        unit_str = f" {stat.unit}" if stat.unit else ""
        avg = _fmt(stat.mean)
        lines.append(f"{stat.indicator} 평균 {avg}{unit_str}로 조사되었다.")

    # 기타 텍스트 지표
    known_text = {"도로명", "도로등급"}
    for ti in section_stats.text_indicators:
        if ti.indicator not in known_text and ti.values:
            values_str = ", ".join(ti.values[:5])
            lines.append(f"{ti.indicator}: {values_str}")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 폐기물 서술문
# ────────────────────────────────────────────

def generate_waste_narrative(
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """폐기물 섹션 서술문을 생성한다."""
    if not _has_any_data(section_stats):
        return _no_data_narrative("waste")

    stats_map = {s.indicator: s for s in section_stats.indicator_stats}
    lines: list[str] = []

    # 도입부
    total = section_stats.total_numeric_count + section_stats.total_text_count
    lines.append(
        f"본 사업지역의 폐기물 발생 현황을 조사한 결과, "
        f"총 {total}건의 데이터를 수집하였다."
    )

    # 생활폐기물
    living_stat = stats_map.get("생활폐기물_발생량")
    if living_stat and living_stat.count > 0:
        unit = living_stat.unit or "톤/일"
        avg = _fmt(living_stat.mean)
        lines.append(
            f"해당 지역의 생활폐기물 발생량은 평균 {avg} {unit}이다."
        )

    # 음식물쓰레기
    food_stat = stats_map.get("음식물쓰레기_발생량")
    if food_stat and food_stat.count > 0:
        unit = food_stat.unit or "톤/일"
        avg = _fmt(food_stat.mean)
        lines.append(f"음식물쓰레기 발생량은 평균 {avg} {unit}이다.")

    # 재활용
    recycle_stat = stats_map.get("재활용_발생량")
    if recycle_stat and recycle_stat.count > 0:
        unit = recycle_stat.unit or "톤/일"
        avg = _fmt(recycle_stat.mean)
        lines.append(f"재활용품 발생량은 평균 {avg} {unit}이다.")

    # 건설폐기물 (수동 입력 항목)
    construction_stat = stats_map.get("건설폐기물_발생량")
    if construction_stat and construction_stat.count > 0:
        unit = construction_stat.unit or "m³/일"
        avg = _fmt(construction_stat.mean)
        lines.append(f"건설폐기물 예상 발생량은 {avg} {unit}이다.")
    else:
        lines.append(
            "건설폐기물 예상 발생량은 사업 계획에 따라 별도 산정이 필요하다."
        )

    # 기타 텍스트 지표
    for ti in section_stats.text_indicators:
        if ti.values:
            values_str = ", ".join(ti.values[:5])
            lines.append(f"{ti.indicator}: {values_str}")

    return "\n".join(lines)


# ────────────────────────────────────────────
# 범용 서술문 (토양 등)
# ────────────────────────────────────────────

def generate_generic_narrative(
    section_def: SectionDefinition,
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """환경기준 비교 대상이 아닌 범용 섹션의 서술문을 생성한다.

    환경기준이 있는 지표에 대해서는 법적 근거를 포함하여 서술한다.
    """
    if not _has_any_data(section_stats):
        return _no_data_narrative()

    lines: list[str] = []

    # 도입부
    total = section_stats.total_numeric_count + section_stats.total_text_count
    if section_stats.total_numeric_count > 0:
        period = _period_str(section_stats)
        lines.append(
            f"본 사업지역의 {section_def.title} 현황을 조사한 결과, "
            f"{period} 동안 총 {total}건의 데이터를 수집하였다."
        )
    else:
        lines.append(
            f"본 사업지역의 {section_def.title} 현황을 조사한 결과, "
            f"총 {total}건의 데이터를 수집하였다."
        )

    # 환경기준 비교 맵 구성
    check_map: dict[str, IndicatorCheckResult] = {}
    if section_check:
        check_map = {r.indicator: r for r in section_check.indicators}

    # 수치형 지표별 서술 (법적 근거 포함)
    for stat in section_stats.indicator_stats:
        if stat.count == 0:
            continue
        unit_str = f" {stat.unit}" if stat.unit else ""
        avg = _fmt(stat.mean)

        cr = check_map.get(stat.indicator)
        if cr and cr.standard_value is not None and cr.status != CheckStatus.NA and cr.legal_basis:
            std_val = _fmt(cr.standard_value)
            legal_ref = _format_legal_ref(cr.legal_basis)
            status = _status_text(cr.status)
            area = _extract_area_from_description(cr.description)
            detail = f"{area} " if area else ""
            lines.append(
                f"{stat.indicator} 평균 {avg}{unit_str}로 "
                f"{legal_ref}({detail}{std_val}{unit_str}) {status} 수준이다."
            )
        else:
            lines.append(f"{stat.indicator} 평균 {avg}{unit_str}로 조사되었다.")

    # 비수치형 지표 서술 (값 목록 형태)
    for ti in section_stats.text_indicators:
        if ti.values:
            values_str = ", ".join(ti.values[:5])
            suffix = f" 외 {len(ti.values) - 5}건" if len(ti.values) > 5 else ""
            lines.append(f"{ti.indicator}: {values_str}{suffix}")

    # 환경기준 비교 결과 (있는 경우)
    if section_check and section_check.has_exceedance:
        fail_names = [
            r.indicator for r in section_check.indicators
            if r.status == CheckStatus.FAIL
        ]
        if fail_names:
            lines.append(
                f"{', '.join(fail_names)}이(가) 환경기준을 초과하여 "
                f"관리 대책 검토가 필요하다."
            )

    return "\n".join(lines)


# ────────────────────────────────────────────
# 미수집 서술문 및 공통 헬퍼
# ────────────────────────────────────────────

def _no_data_narrative(section_key: str = "") -> str:
    """데이터가 수집되지 않은 섹션의 서술문을 반환한다.

    수동 입력이 필요한 섹션에 대해서는 권장 지표 목록을 안내한다.
    """
    guide = _MANUAL_INPUT_GUIDES.get(section_key)
    if guide:
        indicators = ", ".join(guide["indicators"])
        return (
            f"본 분야는 {guide['reason']}으로, "
            f"자동 수집 대상에 해당하지 않는다. "
            f"아래 항목에 대한 수동 입력이 필요하다: {indicators}"
        )
    return "본 분야에 대한 현황 데이터가 수집되지 않았다. 현장조사 및 자료 수집이 필요하다."


# 수동 입력 섹션별 안내 가이드
_MANUAL_INPUT_GUIDES: dict[str, dict] = {
    "landscape": {
        "reason": "현장 시각 조사 및 전문가 판단이 필요한 항목",
        "indicators": [
            "주요 조망점 유무",
            "스카이라인 영향 여부",
            "경관 등급(1~5등급)",
            "주요 경관 자원(산, 하천, 역사경관 등)",
        ],
    },
    "ecology": {
        "reason": "현장 생태 조사 및 전문가 판단이 필요한 항목",
        "indicators": [
            "식물상 종수",
            "동물상 종수",
            "법정보호종",
            "비오톱 유형",
            "녹지자연도",
        ],
    },
    "noise_vibration": {
        "reason": "현장 소음·진동 측정이 필요한 항목",
        "indicators": [
            "소음 Leq 주간(dB(A))",
            "소음 Leq 야간(dB(A))",
            "진동 Lv 주간(dB(V))",
        ],
    },
}


def _has_any_data(section_stats: SectionStats) -> bool:
    """수치형 또는 비수치형 데이터가 하나라도 있는지 확인한다."""
    return (section_stats.total_numeric_count > 0
            or section_stats.total_text_count > 0)


def _text_indicator_map(section_stats: SectionStats) -> dict[str, str]:
    """비수치형 지표를 {지표명: 첫 번째 값} 딕셔너리로 변환한다.

    여러 값이 있으면 쉼표로 연결한다.
    """
    result: dict[str, str] = {}
    for ti in section_stats.text_indicators:
        if ti.values:
            result[ti.indicator] = ", ".join(ti.values[:5])
    return result


# ────────────────────────────────────────────
# Pred-3: 영향 예측 서술문
# ────────────────────────────────────────────

def _generate_air_prediction_narrative(prediction_result: "PredictionResult") -> str:
    """대기질 영향 예측 서술문을 생성한다.

    가우시안 플룸 모델 결과를 기반으로 오염물질별 100m 지점 기여농도,
    현황 농도, 합산 농도, 환경기준 초과 여부를 서술한다.
    """
    lines: list[str] = []
    lines.append(
        "가우시안 플룸 모델을 적용하여 대기오염물질 확산을 예측한 결과는 다음과 같다."
    )

    # 오염물질별 100m 지점 결과 추출
    target_pollutants = ["PM10", "PM2.5", "NO2", "SO2"]
    exceeded_items: list[str] = []

    for pollutant in target_pollutants:
        # 100m 지점 우선; 없으면 첫 번째 예측값 사용
        items_100m = [
            p for p in prediction_result.predictions
            if p.pollutant == pollutant and p.distance_m == 100.0
        ]
        items_all = [
            p for p in prediction_result.predictions
            if p.pollutant == pollutant
        ]
        if not items_all:
            continue

        item = items_100m[0] if items_100m else items_all[0]
        label = "사업지 경계(100m 지점)" if item.distance_m == 100.0 else f"{item.label} 지점"

        if item.standard_value is not None:
            judgment = "초과이다" if item.exceeds_standard else "이내이다"
            lines.append(
                f"{pollutant}: {label}에서 기여농도 {item.predicted_concentration:.2f} {item.unit}으로 "
                f"현황 농도({item.background_concentration:.2f} {item.unit})와 합산 시 "
                f"{item.total_concentration:.2f} {item.unit}으로 "
                f"환경정책기본법 시행령 별표 제1호에 따른 대기환경기준"
                f"({item.standard_value:.4g} {item.unit}) {judgment}."
            )
        else:
            lines.append(
                f"{pollutant}: {label}에서 기여농도 {item.predicted_concentration:.2f} {item.unit}, "
                f"합산 {item.total_concentration:.2f} {item.unit}으로 예측되었다."
            )

        if item.exceeds_standard:
            exceeded_items.append(pollutant)

    if exceeded_items:
        names = ", ".join(exceeded_items)
        lines.append(
            f"{names}의 경우 환경기준을 초과하므로 저감대책 검토 필요하다."
        )

    return "\n".join(lines)


def _generate_noise_prediction_narrative(prediction_result: "PredictionResult") -> str:
    """소음 영향 예측 서술문을 생성한다.

    점음원 거리감쇠 모델 결과를 기반으로 주간/야간 소음도를 서술한다.
    """
    lines: list[str] = []
    lines.append(
        "점음원 거리감쇠 모델을 적용하여 소음 전파를 예측한 결과는 다음과 같다."
    )

    for period_key, period_label, legal_label in [
        ("소음_Leq_주간", "주간", "주간"),
        ("소음_Leq_야간", "야간", "야간"),
    ]:
        items = [
            p for p in prediction_result.predictions
            if p.pollutant == period_key
        ]
        if not items:
            continue

        # 가장 가까운 수음점 (최대 소음 지점)
        nearest = min(items, key=lambda x: x.distance_m if x.distance_m > 0 else float("inf"))

        if nearest.standard_value is not None:
            if nearest.exceeds_standard:
                judgment = "초과하므로 방음대책 검토가 필요하다"
            else:
                judgment = "환경기준 이내이다"
            lines.append(
                f"{period_label}: 가장 가까운 수음점({nearest.label})에서 예측 소음도는 "
                f"{nearest.predicted_concentration:.1f} dB(A)이다. "
                f"현황 소음({nearest.background_concentration:.1f} dB(A))과 에너지 합산 시 "
                f"{nearest.total_concentration:.1f} dB(A)로 {judgment}."
            )
        else:
            lines.append(
                f"{period_label}: 가장 가까운 수음점({nearest.label})에서 "
                f"합산 소음도 {nearest.total_concentration:.1f} dB(A)로 예측되었다."
            )

    return "\n".join(lines)


def _generate_water_prediction_narrative(prediction_result: "PredictionResult") -> str:
    """수질 영향 예측 서술문을 생성한다.

    완전혼합 희석 모델 결과를 기반으로 BOD, COD 등 혼합 후 농도를 서술한다.
    """
    lines: list[str] = []
    lines.append(
        "완전혼합 희석 모델을 적용하여 방류수 혼합 후 수질을 예측한 결과는 다음과 같다."
    )

    # BOD, COD 병합 서술
    bod_item = next(
        (p for p in prediction_result.predictions if p.pollutant == "BOD"), None
    )
    cod_item = next(
        (p for p in prediction_result.predictions if p.pollutant == "COD"), None
    )

    if bod_item and cod_item:
        lines.append(
            f"BOD {bod_item.total_concentration:.2f} {bod_item.unit}, "
            f"COD {cod_item.total_concentration:.2f} {cod_item.unit}로 하천 생활환경기준 수준이다."
        )
    elif bod_item:
        lines.append(
            f"BOD {bod_item.total_concentration:.2f} {bod_item.unit}으로 예측되었다."
        )

    # 기타 항목 서술
    other_pollutants = ["SS", "T-N", "T-P"]
    other_parts: list[str] = []
    for pollutant in other_pollutants:
        item = next(
            (p for p in prediction_result.predictions if p.pollutant == pollutant), None
        )
        if item:
            other_parts.append(
                f"{pollutant} {item.total_concentration:.2f} {item.unit}"
            )
    if other_parts:
        lines.append(", ".join(other_parts) + "로 예측되었다.")

    # 초과 항목 서술
    exceeded = [
        p for p in prediction_result.predictions
        if p.exceeds_standard
    ]
    if exceeded:
        names = ", ".join(p.pollutant for p in exceeded)
        lines.append(
            f"{names}의 경우 환경기준을 초과하므로 추가 처리 대책 검토가 필요하다."
        )

    return "\n".join(lines)


def generate_prediction_narrative(
    section_key: str,
    prediction_result: "PredictionResult",
) -> str:
    """예측 모델 결과를 기반으로 영향 예측 서술문을 생성한다.

    섹션 키에 따라 대기질/소음/수질 전용 서술문을 생성하며,
    해당 없는 섹션은 전문 분석 필요 안내 문구를 반환한다.
    """
    if section_key == "air_quality":
        return _generate_air_prediction_narrative(prediction_result)
    elif section_key == "noise_vibration":
        return _generate_noise_prediction_narrative(prediction_result)
    elif section_key == "water_quality":
        return _generate_water_prediction_narrative(prediction_result)
    else:
        return "본 분야에 대한 영향 예측은 별도 전문 분석이 필요하다."


# ────────────────────────────────────────────
# 메인 디스패처
# ────────────────────────────────────────────

# 섹션 키 → 전용 서술문 생성 함수 매핑
_SECTION_GENERATORS: dict[str, callable] = {
    "air_quality": generate_air_quality_narrative,
    "water_quality": generate_water_quality_narrative,
    "noise_vibration": generate_noise_vibration_narrative,
    "ecology": generate_ecology_narrative,
    "land_use": generate_land_use_narrative,
    "cultural_heritage": generate_cultural_heritage_narrative,
    "traffic": generate_traffic_narrative,
    "waste": generate_waste_narrative,
}


def generate_narrative(
    section_def: SectionDefinition,
    section_stats: SectionStats | None,
    section_check: SectionCheckResult | None,
) -> str:
    """섹션별 서술문을 생성하는 메인 진입점.

    각 섹션에 대해:
    1. 통계 데이터가 없으면(수치+비수치 모두 0건) 미수집 서술문 반환
    2. 전용 생성 함수가 있으면 해당 함수 호출
    3. 없으면 범용 서술문 생성
    """
    if section_stats is None or not _has_any_data(section_stats):
        return _no_data_narrative(section_def.key)

    generator = _SECTION_GENERATORS.get(section_def.key)
    if generator is not None:
        return generator(section_stats, section_check)

    return generate_generic_narrative(section_def, section_stats, section_check)
