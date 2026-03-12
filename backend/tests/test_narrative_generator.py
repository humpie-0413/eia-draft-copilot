"""서술문 템플릿 엔진 테스트.

각 섹션별 서술문 생성, 미수집 섹션 처리, scaffold 통합을 검증한다.
"""

import pytest

from app.services.narrative_generator import (
    _no_data_narrative,
    generate_air_quality_narrative,
    generate_ecology_narrative,
    generate_generic_narrative,
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
from app.services.statistics import IndicatorStats, SectionStats


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
) -> SectionStats:
    total = sum(s.count for s in indicators)
    return SectionStats(
        section_key=section_key,
        title=title,
        total_numeric_count=total,
        indicator_stats=indicators,
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
        """기본 대기질 서술문 생성"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
            _make_indicator_stats("PM2.5_연평균", 12.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 45.0, CheckStatus.PASS),
            _make_check_result("PM2.5_연평균", 15.0, 12.0, CheckStatus.PASS),
        ])

        result = generate_air_quality_narrative(stats, check)

        assert "대기질 현황" in result
        assert "20건" in result
        assert "PM10_연평균" in result
        assert "PM2.5_연평균" in result
        assert "이내" in result
        assert "대기환경기준을 만족" in result

    def test_exceedance_narrative(self):
        """환경기준 초과 시 저감대책 언급"""
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
        assert "저감대책" in result

    def test_no_check_data(self):
        """환경기준 비교 데이터 없이도 서술문 생성"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
        ])

        result = generate_air_quality_narrative(stats, None)

        assert "PM10_연평균" in result
        assert "45" in result

    def test_partial_exceedance(self):
        """일부 지표만 초과"""
        stats = _make_section_stats("air_quality", "대기질", [
            _make_indicator_stats("PM10_연평균", 45.0, unit="ug/m3"),
            _make_indicator_stats("PM2.5_연평균", 20.0, unit="ug/m3"),
        ])
        check = _make_section_check("air_quality", "대기질", [
            _make_check_result("PM10_연평균", 50.0, 45.0, CheckStatus.PASS),
            _make_check_result("PM2.5_연평균", 15.0, 20.0, CheckStatus.FAIL),
        ])

        result = generate_air_quality_narrative(stats, check)

        assert "이내" in result  # PM10
        assert "초과" in result  # PM2.5
        assert "저감대책" in result


# ────────────────────────────────────────────
# 수질 서술문 테스트
# ────────────────────────────────────────────

class TestWaterQualityNarrative:
    def test_basic_narrative_with_grade(self):
        """수질 등급 포함 서술문"""
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
        assert "BOD" in result
        assert "COD" in result
        assert "II등급" in result
        assert "약간 좋음" in result

    def test_exceedance(self):
        """수질 기준 초과 시"""
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
        assert "수질 관리 대책" in result

    def test_other_indicators(self):
        """SS, DO, T-N, T-P 서술"""
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

        assert "T-P" in result
        assert "DO" in result


# ────────────────────────────────────────────
# 소음·진동 서술문 테스트
# ────────────────────────────────────────────

class TestNoiseVibrationNarrative:
    def test_basic_narrative(self):
        """기본 소음 서술문"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 52.0, unit="dB(A)"),
            _make_indicator_stats("소음_Leq_야간", 43.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_주간", 55.0, 52.0, CheckStatus.PASS, "dB(A)", "주간(06~22시)"),
            _make_check_result("소음_Leq_야간", 45.0, 43.0, CheckStatus.PASS, "dB(A)", "야간(22~06시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "소음 현황" in result
        assert "주간 소음도" in result
        assert "야간 소음도" in result
        assert "적합" in result

    def test_nighttime_exceedance(self):
        """야간 소음 초과"""
        stats = _make_section_stats("noise_vibration", "소음·진동", [
            _make_indicator_stats("소음_Leq_주간", 50.0, unit="dB(A)"),
            _make_indicator_stats("소음_Leq_야간", 48.0, unit="dB(A)"),
        ])
        check = _make_section_check("noise_vibration", "소음·진동", [
            _make_check_result("소음_Leq_주간", 55.0, 50.0, CheckStatus.PASS, "dB(A)", "주간(06~22시)"),
            _make_check_result("소음_Leq_야간", 45.0, 48.0, CheckStatus.FAIL, "dB(A)", "야간(22~06시)"),
        ])

        result = generate_noise_vibration_narrative(stats, check)

        assert "방음대책" in result

    def test_vibration_included(self):
        """진동 데이터 포함"""
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
        """기본 생태 서술문"""
        stats = _make_section_stats("ecology", "생태", [
            _make_indicator_stats("식물상_종수", 150.0, unit="종", count=1),
            _make_indicator_stats("동물상_종수", 80.0, unit="종", count=1),
            _make_indicator_stats("녹지자연도", 7.0, unit="등급", count=1),
            _make_indicator_stats("법정보호종", 2.0, unit="종", count=1),
        ])

        result = generate_ecology_narrative(stats, None)

        assert "생태 현황" in result
        assert "식물상 150종" in result
        assert "동물상 80종" in result
        assert "녹지자연도" in result
        assert "법정보호종" in result
        assert "보호 대책" in result

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
# 범용 서술문 테스트
# ────────────────────────────────────────────

class TestGenericNarrative:
    def test_soil_narrative(self):
        """토양 섹션 범용 서술문"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("중금속_납", 15.0, unit="mg/kg"),
            _make_indicator_stats("pH", 6.5, unit=""),
        ])

        result = generate_generic_narrative(section_def, stats, None)

        assert "토양 현황" in result
        assert "중금속_납" in result
        assert "pH" in result

    def test_with_exceedance(self):
        """범용 섹션에서 환경기준 초과"""
        section_def = get_section_definition("soil")
        stats = _make_section_stats("soil", "토양", [
            _make_indicator_stats("중금속_납", 250.0, unit="mg/kg"),
        ])
        check = _make_section_check("soil", "토양", [
            _make_check_result("중금속_납", 200.0, 250.0, CheckStatus.FAIL, "mg/kg"),
        ])

        result = generate_generic_narrative(section_def, stats, check)

        assert "초과" in result
        assert "관리 대책" in result


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

        # 대기질 전용 서술문이 생성되었는지 확인
        assert "대기질 현황" in result

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
            _make_indicator_stats("기온_연평균", 13.5, unit="℃"),
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
        """entries가 있으면 측정 데이터 섹션이 생성"""
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
        assert "PM10_연평균" in result

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
# DOCX 출력물 구조 검증 테스트
# ────────────────────────────────────────────

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
            narrative="본 사업지역 인근의 대기질 현황을 분석한 결과...",
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

        # DOCX 문서에서 텍스트 추출
        all_text = "\n".join(p.text for p in doc.paragraphs)

        # 4부 구조 확인 (Post-5: 번호 체계 N.1/N.2/N.3/N.4)
        assert "1.1 현황 및 영향 분석" in all_text
        assert "1.2 측정 현황 요약" in all_text
        assert "1.3 환경기준 비교" in all_text
        assert "1.4 측정 데이터" in all_text

        # 서술문 포함 확인
        assert "대기질 현황을 분석한 결과" in all_text

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
        # 4부 구조는 나타나지 않아야 함 (데이터 없으므로)
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

        # 테이블에서 데이터 행 수 확인
        # Post-5: 목차 테이블(1개) + 증거 테이블(1개) = 최소 2개
        tables = doc.tables
        assert len(tables) >= 2
        # 마지막 테이블이 증거 테이블: 헤더 1행 + 데이터 5행 = 6행
        last_table = tables[-1]
        assert len(last_table.rows) == 6

        # 부록 참조 문구 확인
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 A 참조" in all_text
