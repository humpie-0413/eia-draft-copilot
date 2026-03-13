"""섹션별 서술문 템플릿 엔진.

Post-1 통계 + Post-2 기준비교 결과를 입력으로 받아
환경영향평가서 초안의 섹션별 서술문을 결정적(deterministic) 방식으로 생성한다.
LLM을 사용하지 않으며, 모든 서술은 수집된 증거 데이터에 기반한다.
"""

from __future__ import annotations

from app.services.section_planner import SectionDefinition
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
)
from app.services.statistics import IndicatorStats, SectionStats, TextIndicatorInfo


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
            lines.append(
                f"{indicator} 평균 {avg} {unit}으로 "
                f"환경기준({std_val} {unit}) {status} 수준이다."
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
            lines.append(
                f"BOD 평균 {bod_avg} {unit}, COD 평균 {cod_avg} {unit}로 "
                f"하천 생활환경기준 {grade}등급({grade_name}) 수준에 해당한다."
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

    # 판정 서술
    if section_check:
        for ind_key, label in [("소음_Leq_주간", "주간"), ("소음_Leq_야간", "야간")]:
            cr = check_map.get(ind_key)
            if cr and cr.status != CheckStatus.NA and cr.standard_value is not None:
                std_val = _fmt(cr.standard_value)
                unit = cr.standard_unit or "dB(A)"
                if cr.status == CheckStatus.PASS:
                    lines.append(
                        f"{label} 소음은 환경기준({std_val} {unit}) 이내로 적합하다."
                    )
                elif cr.status == CheckStatus.FAIL:
                    lines.append(
                        f"{label} 소음은 환경기준({std_val} {unit})을 초과하므로 "
                        f"방음대책 수립이 필요하다."
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
# 범용 서술문 (토양, 교통 등)
# ────────────────────────────────────────────

def generate_generic_narrative(
    section_def: SectionDefinition,
    section_stats: SectionStats,
    section_check: SectionCheckResult | None,
) -> str:
    """환경기준 비교 대상이 아닌 범용 섹션의 서술문을 생성한다."""
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

    # 수치형 지표별 서술
    for stat in section_stats.indicator_stats:
        if stat.count == 0:
            continue
        unit = f" {stat.unit}" if stat.unit else ""
        avg = _fmt(stat.mean)
        lines.append(f"{stat.indicator} 평균 {avg}{unit}로 조사되었다.")

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

def _no_data_narrative() -> str:
    """데이터가 수집되지 않은 섹션의 서술문을 반환한다."""
    return "본 분야에 대한 현황 데이터가 수집되지 않았다. 현장조사 및 자료 수집이 필요하다."


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
        return _no_data_narrative()

    generator = _SECTION_GENERATORS.get(section_def.key)
    if generator is not None:
        return generator(section_stats, section_check)

    return generate_generic_narrative(section_def, section_stats, section_check)
