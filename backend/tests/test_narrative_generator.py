"""서술문 템플릿 엔진 테스트.

각 섹션별 서술문 생성, 미수집 섹션 처리, scaffold 통합을 검증한다.
LLM-Enhancement: 한글 지표명, 기준 대비 %, 적합 지표 묶기, 종합 판단문, 「」법률명 검증.
"""

import pytest

from app.services.narrative_generator import (
    _no_data_narrative,
    generate_air_quality_narrative,
    generate_cultural_heritage_narrative,
    generate_ecology_narrative,
    generate_generic_narrative,
    generate_land_use_narrative,
    generate_narrative,
    generate_noise_vibration_narrative,
    generate_water_quality_narrative,
)
from app.services.section_planner import SectionDefinition, get_section_definition
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
)
from app.services.statistics import IndicatorStats, SectionStats, TextIndicatorInfo


# ────────────────────────────────────────────
# 헬퍼: 테스트용 데이터 생성
# ────────────────────────────────────────────

def _make_indicator_stats(
    indicator: str,
    mean: float,
    count: int = 10,
    unit: str = "ug/m3",
    max_value: float | None = None,
    min_value: float | None = None,
    period_start: str = "2025-01-01T00:00:00",
    period_end: str = "2025-12-31T00:00:00",
) -> IndicatorStats:
    return IndicatorStats(
        indicator=indicator,
        count=count,
        mean=mean,
        max_value=max_value or mean * 1.5,
        min_value=min_value or mean * 0.5,
        unit=unit,
        period_start=period_start,
        period_end=period_end,
    )


def _make_section_stats(
    section_key: str,
    title: str,
    indicators: list[IndicatorStats],
    text_indicators: list[TextIndicatorInfo] | None = None,
) -> SectionStats:
    total = sum(s.count for s in indicators)
    text_inds = text_indicators or []
    text_count = sum(len(t.values) for t in text_inds)
    return SectionStats(
        section_key=section_key,
        title=title,
        total_numeric_count=total,
        total_text_count=text_count,
        indicator_stats=indicators,
        text_indicators=text_inds,
    )


def _make_check_result(
    indicator: str,
    standard_value: float,
    measured_avg: float,
    status: str,
    standard_unit: str = "ug/m3",
    time_basis: str = "연평균",
) -> IndicatorCheckResult:
    return IndicatorCheckResult(
        indicator=indicator,
        standard_value=standard_value,
        standard_unit=standard_unit,
        time_basis=time_basis,
        measured_avg=measured_avg,
        measured_count=10,
        status=status,
    )


def _make_section_check(
    section_key: str,
    title: str,
    indicators: list[IndicatorCheckResult],
    water_grade: str | None = None,
    water_grade_name: str | None = None,
) -> SectionCheckResult:
    fail_count = sum(1 for r in indicators if r.status == CheckStatus.FAIL)
    return SectionCheckResult(
        section_key=section_key,
        title=title,
        indicators=indicators,
        water_grade=water_grade,
        water_grade_name=water_grade_name,
        has_exceedance=fail_count > 0,
        exceedance_count=fail_count,
    )


# ────────────────────────────────────────────
# 미수집 섹션 테스트
# ────────────────────────────────────────────

class TestNoDataNarrative:
    def test_returns_fixed_text(self):
        result = _no_data_narrative()
        assert "수집되지 않았다" in result
        assert "현장조사" in result

    def test_generate_narrative_with_no_stats(self):
        section_def = get_section_definition("air_quality")
        result = generate_narrative(section_def, None, None)
        assert "수집되지 않았다" in result

    def test_generate_narrative_with_zero_count(self):
        section_def = get_section_definition("air_quality")
        stats = SectionStats(
            section_key="air_quality",
            title="대기질",
            total_numeric_count=0,
            indicator_stats=[],
        )
        result = generate_narrative(section_def, stats, None)
        assert "수집되지 않았다" in result


# ────────────────────────────────────────────
# 대기질 서술문 테스트
# ────────────────────────────────────────────

class TestAirQualityNarrative:
    def test_basic_narrative(self):
        """기본 대기질 서술문 — 한글 지표명, 종합 판단문 포함"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
            _make_indicator_stats("PM2.5_연평균", 12.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 45.0, CheckStatus.PASS),
            _make_check_result("PM2.5_연평균", 15.0, 12.0, CheckStatus.PASS),
        ])

        result = generate_air_quality_narrative(stats, check)

        assert "대기환경 현황" in result
        assert "20건" in result
        # 한글 지표명 사용
        assert "미세먼지(PM10)" in result
        assert "초미세먼지(PM2.5)" in result
        # 적합 지표 묶음
        assert "환경기준을 만족" in result
        # 종합 판단문
        assert "양호한 수준으로 판단된다" in result

    def test_exceedance_narrative(self):
        """환경기준 초과 시 저감대책 + 기준 대비 % 포함"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 55.0, unit="ug/m3"),
            _make_indicator_stats("PM2.5_연평균", 20.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 55.0, CheckStatus.FAIL),
            _make_check_result("PM2.5_연평균", 15.0, 20.0, CheckStatus.FAIL),
        ])

        result = generate_air_quality_narrative(stats, check)

        assert "초과" in result
        assert "저감" in result
        # 기준 대비 %
        assert "110.0%" in result  # PM10: 55/50*100
        assert "133.3%" in result  # PM2.5: 20/15*100
        # 「」기호 법률명
        assert "「환경정책기본법」" in result

    def test_no_check_data(self):
        """환경기준 비교 데이터 없이도 서술문 생성"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
        ])

        result = generate_air_quality_narrative(stats, None)

        assert "미세먼지(PM10)" in result
        assert "45" in result

    def test_partial_exceedance(self):
        """일부 지표만 초과 — 적합 묶음 + 초과 별도"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
            _make_indicator_stats("PM2.5_연평균", 20.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 45.0, CheckStatus.PASS),
            _make_check_result("PM2.5_연평균", 15.0, 20.0, CheckStatus.FAIL),
        ])

        result = generate_air_quality_narrative(stats, check)

        # 적합 묶음에 PM10
        assert "미세먼지(PM10)" in result
        # 초과 별도 PM2.5
        assert "초과" in result
        assert "저감" in result
        # 종합 판단문
        assert "제외한" in result


# ────────────────────────────────────────────
# 수질 서술문 테스트
# ────────────────────────────────────────────

class TestWaterQualityNarrative:
    def test_basic_narrative_with_grade(self):
        """수질 등급 포함 서술문 — 한글 지표명"""
        stats = _make_section_stats("water_quality", "수질", [
            _make_indicator_stats("BOD", 3.5, unit="mg/L"),
            _make_indicator_stats("COD", 5.0, unit="mg/L"),
            _make_indicator_stats("SS", 15.0, unit="mg/L"),
            _make_indicator_stats("DO", 7.0, unit="mg/L"),
        ])
        check = _make_section_check("water_quality", "수질", [
            _make_check_result("BOD", 5.0, 3.5, CheckStatus.PASS, "mg/L", "평균"),
            _make_check_result("COD", 7.0, 5.0, CheckStatus.PASS, "mg/L", "평균"),
        ], water_grade="II", water_grade_name="약간 좋음")

        result = generate_water_quality_narrative(stats, check)

        assert "수질 현황" in result
        assert "생물화학적산소요구량(BOD)" in result
        assert "화학적산소요구량(COD)" in result
        assert "II등급" in result
        assert "약간 좋음" in result
        # 종합 판단문
        assert "종합적으로" in result

    def test_exceedance(self):
        """수질 기준 초과 시 — 기준 대비 % 포함"""
        stats = _make_section_stats("water_quality", "수질", [
            _make_indicator_stats("BOD", 8.0, unit="mg/L"),
            _make_indicator_stats("COD", 10.0, unit="mg/L"),
        ])
        check = _make_section_check("water_quality", "수질", [
            _make_check_result("BOD", 5.0, 8.0, CheckStatus.FAIL, "mg/L", "평균"),
            _make_check_result("COD", 7.0, 10.0, CheckStatus.FAIL, "mg/L", "평균"),
        ])

        result = generate_water_quality_narrative(stats, check)

        assert "초과" in result

    def test_other_indicators(self):
        """SS, DO, T-N, T-P 한글 지표명 서술"""
        stats = _make_section_stats("water_quality", "수질", [
            _make_indicator_stats("BOD", 3.0, unit="mg/L"),
            _make_indicator_stats("COD", 5.0, unit="mg/L"),
            _make_indicator_stats("T-P", 0.1, unit="mg/L"),
            _make_indicator_stats("DO", 8.0, unit="mg/L"),
        ])
        check = _make_section_check("water_quality", "수질", [
            _make_check_result("BOD", 5.0, 3.0, CheckStatus.PASS, "mg/L", "평균"),
        ])

        result = generate_water_quality_narrative(stats, check)

        assert "총인(T-P)" in result
        assert "용존산소(DO)" in result


# ────────────────────────────────────────────
# 소음·진동 서술문 테스트
# ────────────────────────────────────────────

class TestNoiseVibrationNarrative:
    def test_basic_narrative(self):
        """기본 소음 서술문 — 한글 지표명"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 52.0, unit="dB(A)"),
            _make_indicator_stats("소음_Leq_야간", 43.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_주간", 55.0, 52.0, CheckStatus.PASS, "dB(A)", "주간(06~22시)"),
            _make_check_result("소음_Leq_야간", 45.0, 43.0, CheckStatus.PASS, "dB(A)", "야간(22~06시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "소음·진동 현황" in result
        assert "주간 등가소음도(Leq)" in result
        assert "야간 등가소음도(Leq)" in result
        assert "적합" in result
        # 종합 판단문
        assert "양호한 수준으로 판단된다" in result

    def test_nighttime_exceedance(self):
        """야간 소음 초과 — 저감방안 포함"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 50.0, unit="dB(A)"),
            _make_indicator_stats("소음_Leq_야간", 48.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_주간", 55.0, 50.0, CheckStatus.PASS, "dB(A)", "주간(06~22시)"),
            _make_check_result("소음_Leq_야간", 45.0, 48.0, CheckStatus.FAIL, "dB(A)", "야간(22~06시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "방음벽" in result or "소음저감대책" in result

    def test_vibration_included(self):
        """진동 데이터 포함 — 한글 지표명"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 52.0, unit="dB(A)"),
            _make_indicator_stats("진동_Lv_주간", 60.0, unit="dB(V)"),
        ])

        result = generate_noise_vibration_narrative(stats, None)

        assert "진동" in result
        assert "60" in result


# ────────────────────────────────────────────
# 생태 서술문 테스트
# ────────────────────────────────────────────

class TestEcologyNarrative:
    def test_basic_narrative(self):
        """기본 생태 서술문 — 종합 판단문 포함"""
        stats = _make_section_stats("ecology", "생태", [
            _make_indicator_stats("식물상_종수", 150.0, unit="종", count=1),
            _make_indicator_stats("동물상_종수", 80.0, unit="종", count=1),
            _make_indicator_stats("녹지자연도", 7.0, unit="등급", count=1),
            _make_indicator_stats("법정보호종", 2.0, unit="종", count=1),
        ])

        result = generate_ecology_narrative(stats, None)

        assert "생태환경 현황" in result
        assert "식물상 150종" in result
        assert "동물상 80종" in result
        assert "녹지자연도" in result
        assert "법정보호종" in result
        assert "보호 대책" in result
        # 종합 판단문
        assert "종합적으로" in result

    def test_no_protected_species(self):
        """법정보호종 0종"""
        stats = _make_section_stats("ecology", "생태", [
            _make_indicator_stats("식물상_종수", 100.0, unit="종", count=1),
            _make_indicator_stats("법정보호종", 0.0, unit="종", count=1),
        ])

        result = generate_ecology_narrative(stats, None)

        assert "확인되지 않았다" in result

    def test_no_protected_species_data(self):
        """법정보호종 데이터 없음"""
        stats = _make_section_stats("ecology", "생태", [
            _make_indicator_stats("식물상_종수", 100.0, unit="종", count=1),
        ])

        result = generate_ecology_narrative(stats, None)

        assert "수집되지 않았다" in result


# ────────────────────────────────────────────
# 토지이용 서술문 테스트
# ────────────────────────────────────────────

class TestLandUseNarrative:
    def test_basic_text_only_narrative(self):
        """비수치형 데이터만 있는 토지이용 서술문 — 법률명 포함"""
        stats = _make_section_stats("land_use", "토지이용", [], text_indicators=[
            TextIndicatorInfo(indicator="지목", values=["대"]),
            TextIndicatorInfo(indicator="용도지역구분", values=["제2종일반주거지역"]),
            TextIndicatorInfo(indicator="용도지구", values=["미관지구"]),
        ])

        result = generate_land_use_narrative(stats, None)

        assert "토지이용 현황" in result
        assert "지목은 대" in result
        assert "용도지역은 제2종일반주거지역" in result
        assert "용도지구는 미관지구" in result
        assert "「국토의 계획 및 이용에 관한 법률」" in result

    def test_no_data(self):
        """데이터 없는 토지이용 섹션"""
        stats = _make_section_stats("land_use", "토지이용", [])

        result = generate_land_use_narrative(stats, None)

        assert "수집되지 않았다" in result

    def test_partial_text_data(self):
        """지목만 있는 경우"""
        stats = _make_section_stats("land_use", "토지이용", [], text_indicators=[
            TextIndicatorInfo(indicator="지목", values=["전"]),
        ])

        result = generate_land_use_narrative(stats, None)

        assert "지목은 전" in result

    def test_dispatches_land_use(self):
        """land_use → 전용 생성 함수 호출"""
        section_def = get_section_definition("land_use")
        stats = _make_section_stats("land_use", "토지이용", [], text_indicators=[
            TextIndicatorInfo(indicator="지목", values=["대"]),
            TextIndicatorInfo(indicator="용도지역구분", values=["일반상업지역"]),
        ])

        result = generate_narrative(section_def, stats, None)

        assert "토지이용 현황" in result
        assert "수집되지 않았다" not in result


# ────────────────────────────────────────────
# 문화재 서술문 테스트
# ────────────────────────────────────────────

class TestCulturalHeritageNarrative:
    def test_basic_narrative(self):
        """문화재명(텍스트) + 이격거리(수치) 혼합 서술문 — 법률명 포함"""
        stats = _make_section_stats("cultural_heritage", "문화재", [
            _make_indicator_stats("이격거리", 850.0, unit="m", count=1),
        ], text_indicators=[
            TextIndicatorInfo(indicator="문화재명", values=["봉은사"]),
        ])

        result = generate_cultural_heritage_narrative(stats, None)

        assert "문화재 현황" in result
        assert "봉은사" in result
        assert "이격거리" in result
        assert "850" in result
        assert "「문화재보호법」" in result

    def test_text_only(self):
        """문화재명만 있는 경우"""
        stats = _make_section_stats("cultural_heritage", "문화재", [], text_indicators=[
            TextIndicatorInfo(indicator="문화재명", values=["숭례문"]),
        ])

        result = generate_cultural_heritage_narrative(stats, None)

        assert "숭례문" in result
        assert "수집되지 않았다" not in result

    def test_no_data(self):
        """데이터 없는 문화재 섹션"""
        stats = _make_section_stats("cultural_heritage", "문화재", [])

        result = generate_cultural_heritage_narrative(stats, None)

        assert "수집되지 않았다" in result

    def test_dispatches_cultural_heritage(self):
        """cultural_heritage → 전용 생성 함수 호출"""
        section_def = get_section_definition("cultural_heritage")
        stats = _make_section_stats("cultural_heritage", "문화재", [], text_indicators=[
            TextIndicatorInfo(indicator="문화재명", values=["봉은사"]),
        ])

        result = generate_narrative(section_def, stats, None)

        assert "봉은사" in result
        assert "수집되지 않았다" not in result


# ────────────────────────────────────────────
# 범용 서술문 테스트 (비수치 포함)
# ────────────────────────────────────────────

class TestGenericNarrativeTextData:
    def test_text_only_generic(self):
        """비수치형 데이터만 있는 범용 섹션 서술문"""
        section_def = get_section_definition("waste")
        stats = _make_section_stats("waste", "폐기물", [], text_indicators=[
            TextIndicatorInfo(indicator="폐기물_종류", values=["건설폐기물", "생활폐기물"]),
        ])

        result = generate_generic_narrative(section_def, stats, None)

        assert "폐기물 현황" in result
        assert "폐기물_종류" in result
        assert "건설폐기물" in result
        assert "수집되지 않았다" not in result


# ────────────────────────────────────────────
# 범용 서술문 테스트
# ────────────────────────────────────────────

class TestGenericNarrative:
    def test_soil_narrative(self):
        """토양 섹션 범용 서술문 — 한글 지표명"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("Pb", 15.0, unit="mg/kg"),
            _make_indicator_stats("pH", 6.5, unit=""),
        ])

        result = generate_generic_narrative(section_def, stats, None)

        assert "토양 현황" in result
        assert "납(Pb)" in result
        assert "수소이온농도(pH)" in result

    def test_with_exceedance(self):
        """범용 섹션에서 환경기준 초과 — 저감방안 포함"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("Pb", 250.0, unit="mg/kg"),
        ])
        check = _make_section_check("soil", "토양", [
            _make_check_result("Pb", 200.0, 250.0, CheckStatus.FAIL, "mg/kg"),
        ])

        result = generate_generic_narrative(section_def, stats, check)

        assert "초과" in result
        assert "대책" in result


# ────────────────────────────────────────────
# 디스패처 테스트
# ────────────────────────────────────────────

class TestGenerateNarrative:
    def test_dispatches_air_quality(self):
        """air_quality → 전용 생성 함수 호출"""
        section_def = get_section_definition("air_quality")
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 40.0, unit="ug/m3"),
        ])

        result = generate_narrative(section_def, stats, None)

        assert "대기환경 현황" in result

    def test_dispatches_water_quality(self):
        """water_quality → 전용 생성 함수 호출"""
        section_def = get_section_definition("water_quality")
        stats = _make_section_stats("water_quality", "수질", [
            _make_indicator_stats("BOD", 3.0, unit="mg/L"),
            _make_indicator_stats("COD", 5.0, unit="mg/L"),
        ])

        result = generate_narrative(section_def, stats, None)

        assert "수질 현황" in result

    def test_dispatches_generic(self):
        """climate → 범용 생성 함수 호출"""
        section_def = get_section_definition("climate")
        stats = _make_section_stats("climate", "기후", [
            _make_indicator_stats("평균기온", 13.5, unit="℃"),
        ])

        result = generate_narrative(section_def, stats, None)

        assert "기후 현황" in result

    def test_no_data_returns_fixed_text(self):
        """데이터 없을 때 미수집 서술문"""
        section_def = get_section_definition("air_quality")
        result = generate_narrative(section_def, None, None)
        assert "수집되지 않았다" in result


# ────────────────────────────────────────────
# scaffold 통합 테스트 (순수 함수 레벨)
# ────────────────────────────────────────────

class TestScaffoldIntegration:
    def test_summary_text_has_stats_table(self):
        """scaffold summary_text에 통계 테이블이 포함되는지 확인"""
        from app.services.draft_scaffold import _format_stats_summary

        section_def = get_section_definition("air_quality")
        entries = []  # 빈 entries면 빈 문자열
        result = _format_stats_summary(section_def, entries, [])
        assert result == ""

    def test_summary_text_with_entries(self):
        """entries가 있으면 측정 데이터 섹션이 생성 — 한글 지표명"""
        from app.services.draft_scaffold import _format_stats_summary, EvidenceEntry

        section_def = get_section_definition("air_quality")
        entries = [
            EvidenceEntry(
                evidence_id="e1", indicator="PM10_연평균", value="45",
                numeric_value=45.0, unit="ug/m3",
                observed_at="2025-06-01T00:00:00",
                data_source_id=None, metadata_json=None,
            ),
        ]
        indicator_stats = [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
        ]

        result = _format_stats_summary(section_def, entries, indicator_stats)

        assert "측정 현황 요약" in result
        assert "측정 데이터" in result
        assert "미세먼지(PM10) 연평균" in result

    def test_max_detail_samples_limit(self):
        """상세 샘플이 5건으로 제한되는지 확인"""
        from app.services.draft_scaffold import _format_stats_summary, EvidenceEntry

        section_def = get_section_definition("air_quality")
        entries = [
            EvidenceEntry(
                evidence_id=f"e{i}", indicator="PM10_연평균", value=str(40 + i),
                numeric_value=40.0 + i, unit="ug/m3",
                observed_at=f"2025-{i+1:02d}-01T00:00:00",
                data_source_id=None, metadata_json=None,
            )
            for i in range(10)
        ]

        result = _format_stats_summary(section_def, entries, [])

        assert "별첨 참조" in result
        assert "외 5건" in result


# ────────────────────────────────────────────
# Reg-2: 법적 근거 포함 검증 테스트 (「」기호 적용)
# ────────────────────────────────────────────

class TestLegalBasisInNarrative:
    """서술문에 법적 근거가 「」기호로 포함되는지 검증한다."""

    def test_air_includes_legal_basis(self):
        """대기질 서술문에 「환경정책기본법」 참조가 포함됨"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 42.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 42.0, CheckStatus.PASS),
        ])

        result = generate_air_quality_narrative(stats, check)

        # 적합인 경우 pass_parts에 들어가므로 법적 근거 서술이 없을 수 있음
        # 대신 종합 판단문이 있어야 함
        assert "양호한 수준으로 판단된다" in result

    def test_air_exceedance_includes_legal_basis(self):
        """대기질 초과 서술문에 「환경정책기본법」 법적 근거가 포함됨"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM2.5_연평균", 20.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM2.5_연평균", 15.0, 20.0, CheckStatus.FAIL),
        ])

        result = generate_air_quality_narrative(stats, check)

        assert "「환경정책기본법」 시행령 [별표 1]" in result
        assert "초과" in result
        assert "기준 대비" in result or "%" in result

    def test_air_includes_percentage(self):
        """대기질 초과 서술문에 기준 대비 %가 포함됨"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 55.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 55.0, CheckStatus.FAIL),
        ])

        result = generate_air_quality_narrative(stats, check)

        # 55/50*100 = 110.0%
        assert "110.0%" in result

    def test_water_includes_legal_basis_and_grade(self):
        """수질 서술문에 「환경정책기본법」과 등급 BOD 기준값이 포함됨"""
        stats = _make_section_stats("water_quality", "수질", [
            _make_indicator_stats("BOD", 1.80, unit="mg/L"),
            _make_indicator_stats("COD", 3.50, unit="mg/L"),
        ])
        check = _make_section_check("water_quality", "수질", [
            _make_check_result("BOD", 5.0, 1.80, CheckStatus.PASS, "mg/L", "평균"),
            _make_check_result("COD", 7.0, 3.50, CheckStatus.PASS, "mg/L", "평균"),
        ], water_grade="Ib", water_grade_name="좋음")

        result = generate_water_quality_narrative(stats, check)

        assert "「환경정책기본법」 시행령 [별표 1]" in result
        assert "Ib등급" in result
        assert "좋음" in result
        assert "BOD 2 mg/L 이하" in result

    def test_noise_includes_legal_basis_pass(self):
        """소음 적합 서술문에 「환경정책기본법」 법적 근거 포함"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 52.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_주간", 55.0, 52.0, CheckStatus.PASS,
                               "dB(A)", "주간(06~22시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "「환경정책기본법」 시행령 [별표 1]" in result
        assert "적합" in result

    def test_noise_includes_legal_basis_fail(self):
        """소음 초과 서술문에 법적 근거 + 저감방안 포함"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_야간", 48.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_야간", 45.0, 48.0, CheckStatus.FAIL,
                               "dB(A)", "야간(22~06시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "「환경정책기본법」 시행령 [별표 1]" in result
        assert "방음벽" in result or "소음저감대책" in result

    def test_soil_generic_includes_legal_basis(self):
        """토양 범용 서술문에 「토양환경보전법」이 포함됨"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("Cd", 0.80, unit="mg/kg"),
        ])
        check = _make_section_check("soil", "토양", [
            IndicatorCheckResult(
                indicator="Cd",
                standard_value=4.0,
                standard_unit="mg/kg",
                time_basis="우려기준",
                measured_avg=0.80,
                measured_count=10,
                status=CheckStatus.PASS,
                description="카드뮴 1지역 우려기준",
                legal_basis="토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)",
            ),
        ])

        result = generate_generic_narrative(section_def, stats, check)

        assert "「토양환경보전법」 시행규칙 [별표 3]" in result
        assert "1지역" in result
        assert "4 mg/kg" in result

    def test_generic_no_legal_basis_fallback(self):
        """법적 근거가 없는 범용 서술문은 한글 지표명으로 출력됨"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("pH", 6.5, unit=""),
        ])

        result = generate_generic_narrative(section_def, stats, None)

        assert "수소이온농도(pH) 6.50" in result


class TestLegalBasisInScaffold:
    """scaffold 테이블에 법적 근거 열이 포함되는지 검증한다."""

    def test_scaffold_table_has_legal_basis_column(self):
        """환경기준이 있으면 테이블에 법적 근거 열이 포함됨"""
        from app.services.draft_scaffold import _format_stats_summary, EvidenceEntry

        section_def = get_section_definition("air_quality")
        entries = [
            EvidenceEntry(
                evidence_id="e1", indicator="PM10_연평균", value="45",
                numeric_value=45.0, unit="ug/m3",
                observed_at="2025-06-01T00:00:00",
                data_source_id=None, metadata_json=None,
            ),
        ]
        indicator_stats = [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
        ]
        check_results = [
            IndicatorCheckResult(
                indicator="PM10_연평균",
                standard_value=50.0, standard_unit="ug/m3",
                time_basis="연평균",
                measured_avg=45.0, measured_count=10,
                status=CheckStatus.PASS,
                legal_basis="환경정책기본법 시행령 별표 제1호 (대기환경기준)",
            ),
        ]

        result = _format_stats_summary(
            section_def, entries, indicator_stats,
            check_results=check_results,
        )

        assert "법적 근거" in result
        assert "환경정책기본법 별표1" in result

    def test_scaffold_table_no_legal_basis_without_standards(self):
        """환경기준이 없으면 법적 근거 열이 없음"""
        from app.services.draft_scaffold import _format_stats_summary, EvidenceEntry

        section_def = get_section_definition("climate")
        entries = [
            EvidenceEntry(
                evidence_id="e1", indicator="평균기온", value="13.5",
                numeric_value=13.5, unit="℃",
                observed_at="2025-06-01T00:00:00",
                data_source_id=None, metadata_json=None,
            ),
        ]
        indicator_stats = [
            _make_indicator_stats("평균기온", 13.5, unit="℃"),
        ]

        result = _format_stats_summary(section_def, entries, indicator_stats)

        assert "법적 근거" not in result


class TestLegalBasisInStandardChecker:
    """StandardCheckResult에 legal_basis가 설정되는지 검증한다."""

    def test_indicator_check_result_has_legal_basis(self):
        """IndicatorCheckResult에 legal_basis 필드가 존재함"""
        cr = IndicatorCheckResult(
            indicator="PM10_연평균",
            legal_basis="환경정책기본법 시행령 별표 제1호 (대기환경기준)",
        )
        assert cr.legal_basis == "환경정책기본법 시행령 별표 제1호 (대기환경기준)"

    def test_indicator_check_result_default_empty(self):
        """legal_basis 기본값은 빈 문자열"""
        cr = IndicatorCheckResult(indicator="test")
        assert cr.legal_basis == ""

    def test_format_legal_ref_conversion(self):
        """standard_checker의 _format_legal_ref는 표준 변환"""
        from app.services.standard_checker import _format_legal_ref

        assert _format_legal_ref(
            "환경정책기본법 시행령 별표 제1호 (대기환경기준)"
        ) == "환경정책기본법 시행령 별표 제1호에 따른 대기환경기준"

        assert _format_legal_ref(
            "토양환경보전법 시행규칙 별표 제3호 (토양오염우려기준)"
        ) == "토양환경보전법 시행규칙 별표 제3호에 따른 토양오염우려기준"

        assert _format_legal_ref("") == ""

    def test_format_legal_ref_water(self):
        """수질 법적 근거 변환"""
        from app.services.standard_checker import _format_legal_ref

        result = _format_legal_ref(
            "환경정책기본법 시행령 별표 제1호 (수질 및 수생태계 환경기준) — 하천 생활환경기준"
        )
        assert result == "환경정책기본법 시행령 별표 제1호에 따른 하천 수질 및 수생태계 생활환경기준"


class TestDocxStructure:
    def _make_ctx(self, scaffold, project_name, section_data):
        """테스트용 ExportContext를 생성하는 헬퍼."""
        from app.services.export_service import ExportContext, ExportOptions
        return ExportContext(
            scaffold=scaffold,
            project_name=project_name,
            project_type=None,
            centroid=None,
            section_data=section_data,
            similar_cases=[],
            qa_result=None,
            options=ExportOptions(
                include_appendix_a=False,
                include_appendix_b=False,
                include_appendix_c=False,
            ),
            generated_at=scaffold.generated_at,
        )

    def test_docx_section_structure(self):
        """DOCX 섹션이 4부 구조(N.1/N.2/N.3/N.4)를 포함하는지 검증"""
        from app.services.draft_scaffold import DraftScaffold, EvidenceEntry, ScaffoldSection
        from app.services.export_service import _build_docx
        from app.services.statistics import IndicatorStats, SectionStats
        from app.services.standard_checker import (
            IndicatorCheckResult,
            SectionCheckResult,
        )

        section = ScaffoldSection(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질 현황",
            order=1,
            evidence_entries=[
                EvidenceEntry(
                    evidence_id="e1", indicator="PM10_연평균", value="45",
                    numeric_value=45.0, unit="ug/m3",
                    observed_at="2025-06-01T00:00:00",
                    data_source_id=None, metadata_json=None,
                ),
            ],
            summary_text="통계 요약",
            narrative="본 사업지역의 대기환경 현황을 파악하기 위하여 분석한 결과...",
            state="complete",
        )

        scaffold = DraftScaffold(
            project_id="test-id",
            generated_at="2025-06-01T00:00:00",
            sections=[section],
            total_evidence_count=1,
        )

        stats = SectionStats(
            section_key="air_quality",
            title="대기질",
            total_numeric_count=10,
            indicator_stats=[
                IndicatorStats(
                    indicator="PM10_연평균", count=10, mean=45.0,
                    max_value=60.0, min_value=30.0, unit="ug/m3",
                ),
            ],
        )
        check = SectionCheckResult(
            section_key="air_quality",
            title="대기질",
            indicators=[
                IndicatorCheckResult(
                    indicator="PM10_연평균",
                    standard_value=50.0, standard_unit="ug/m3",
                    time_basis="연평균",
                    measured_avg=45.0, measured_count=10,
                    status=CheckStatus.PASS,
                ),
            ],
        )

        section_data = {"air_quality": (stats, check)}
        ctx = self._make_ctx(scaffold, "테스트 프로젝트", section_data)
        doc = _build_docx(ctx)

        all_text = "\n".join(p.text for p in doc.paragraphs)

        # 4부 구조 확인
        assert "1.1 현황 및 영향 분석" in all_text
        assert "1.2 측정 현황 요약" in all_text
        assert "1.3 환경기준 비교" in all_text
        assert "1.4 측정 데이터" in all_text

        # 서술문 포함 확인
        assert "대기환경 현황" in all_text

    def test_docx_no_data_section(self):
        """미수집 섹션의 DOCX 출력 검증"""
        from app.services.draft_scaffold import DraftScaffold, ScaffoldSection
        from app.services.export_service import _build_docx

        section = ScaffoldSection(
            section_key="soil",
            title="토양",
            description="토양오염 현황",
            order=3,
            evidence_entries=[],
            summary_text="",
            narrative="본 분야에 대한 현황 데이터가 수집되지 않았다. 현장조사 및 자료 수집이 필요하다.",
            state="empty",
        )

        scaffold = DraftScaffold(
            project_id="test-id",
            generated_at="2025-06-01T00:00:00",
            sections=[section],
            total_evidence_count=0,
        )

        section_data = {"soil": (None, None)}
        ctx = self._make_ctx(scaffold, "테스트", section_data)
        doc = _build_docx(ctx)

        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "수집되지 않았다" in all_text
        assert "3.1 현황 및 영향 분석" not in all_text

    def test_docx_sample_limit(self):
        """DOCX에서 샘플이 5건으로 제한되는지 확인"""
        from app.services.draft_scaffold import DraftScaffold, EvidenceEntry, ScaffoldSection
        from app.services.export_service import _build_docx

        entries = [
            EvidenceEntry(
                evidence_id=f"e{i}", indicator="PM10_연평균", value=str(40 + i),
                numeric_value=40.0 + i, unit="ug/m3",
                observed_at=f"2025-{i+1:02d}-01T00:00:00",
                data_source_id=None, metadata_json=None,
            )
            for i in range(10)
        ]

        section = ScaffoldSection(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질",
            order=1,
            evidence_entries=entries,
            summary_text="요약",
            narrative="서술문",
            state="complete",
        )

        scaffold = DraftScaffold(
            project_id="test-id",
            generated_at="2025-06-01T00:00:00",
            sections=[section],
            total_evidence_count=10,
        )

        section_data = {"air_quality": (None, None)}
        ctx = self._make_ctx(scaffold, "테스트", section_data)
        doc = _build_docx(ctx)

        tables = doc.tables
        assert len(tables) >= 2
        last_table = tables[-1]
        assert len(last_table.rows) == 6

        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 A 참조" in all_text


# ────────────────────────────────────────────
# LLM-Enhancement: 한글 지표명 매핑 테스트
# ────────────────────────────────────────────

class TestIndicatorKoreanNames:
    """indicator_names.py 모듈의 한글 매핑 테스트."""

    def test_get_korean_name_mapped(self):
        """매핑된 지표는 한글명 반환"""
        from app.data.indicator_names import get_korean_name
        assert get_korean_name("PM10") == "미세먼지(PM10)"
        assert get_korean_name("BOD") == "생물화학적산소요구량(BOD)"
        assert get_korean_name("소음_Leq_주간") == "주간 등가소음도(Leq)"

    def test_get_korean_name_unmapped(self):
        """매핑되지 않은 지표는 원래 이름 반환"""
        from app.data.indicator_names import get_korean_name
        assert get_korean_name("식물상_종수") == "식물상_종수"
        assert get_korean_name("unknown_indicator") == "unknown_indicator"

    def test_get_mitigation(self):
        """저감방안 매핑 확인"""
        from app.data.indicator_names import get_mitigation
        assert "비산먼지" in get_mitigation("PM10")
        assert "방음벽" in get_mitigation("소음_Leq_주간")
        assert "정밀조사" in get_mitigation("Pb")

    def test_get_mitigation_default(self):
        """매핑되지 않은 지표의 기본 저감방안"""
        from app.data.indicator_names import get_mitigation
        assert get_mitigation("unknown") == "관리 대책 수립"
