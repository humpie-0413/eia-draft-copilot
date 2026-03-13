"""법령 데이터 무결성 및 구조 테스트.

Reg-1에서 구축한 법령 데이터의 완전성과 정합성을 검증한다.
Reg-3에서 추가: QA 규칙 R007/R008 법적 필수 항목 검증 테스트.
"""

import pytest

from app.data.env_standards import (
    AIR_STANDARDS,
    NOISE_STANDARDS,
    SOIL_STANDARDS,
    STANDARDS_BY_CATEGORY,
    WATER_STANDARDS,
    Standard,
    get_standard_for_indicator,
    get_standards_for_category,
)
from app.data.regulations.area_classifications import (
    NOISE_AREA_GENERAL,
    NOISE_AREA_ROADSIDE,
    NOISE_AREA_STANDARDS,
    get_noise_area_info,
    get_noise_standard,
)
from app.data.regulations.legal_references import (
    AIR_INDICATOR_REFS,
    ALL_INDICATOR_REFS,
    CATEGORY_LEGAL_REFS,
    NOISE_INDICATOR_REFS,
    SOIL_INDICATOR_REFS,
    WATER_INDICATOR_REFS,
    get_category_legal_reference,
    get_legal_reference,
)
from app.data.regulations.required_items import (
    REQUIRED_BY_TYPE,
    get_project_type_requirement,
    get_required_indicators,
    get_required_sections,
)


# ────────────────────────────────────────────
# 1. 법적 근거 매핑 무결성 테스트
# ────────────────────────────────────────────


class TestLegalReferences:
    """법적 근거 매핑 무결성 테스트."""

    def test_all_air_standards_have_legal_reference(self):
        """모든 대기 기준에 법적 근거가 매핑되어 있어야 한다."""
        for std in AIR_STANDARDS:
            ref = get_legal_reference(std.indicator)
            assert ref is not None, f"대기 지표 '{std.indicator}'에 법적 근거 누락"
            assert ref.standard_value == std.limit_value, (
                f"대기 지표 '{std.indicator}' 기준값 불일치: "
                f"env_standards={std.limit_value}, legal_ref={ref.standard_value}"
            )

    def test_all_water_standards_have_legal_reference(self):
        """모든 수질 기준에 법적 근거가 매핑되어 있어야 한다."""
        for std in WATER_STANDARDS:
            ref = get_legal_reference(std.indicator)
            assert ref is not None, f"수질 지표 '{std.indicator}'에 법적 근거 누락"
            assert ref.standard_value == std.limit_value

    def test_all_noise_standards_have_legal_reference(self):
        """모든 소음 기준에 법적 근거가 매핑되어 있어야 한다."""
        for std in NOISE_STANDARDS:
            ref = get_legal_reference(std.indicator)
            assert ref is not None, f"소음 지표 '{std.indicator}'에 법적 근거 누락"

    def test_all_soil_standards_have_legal_reference(self):
        """모든 토양 기준에 법적 근거가 매핑되어 있어야 한다."""
        for std in SOIL_STANDARDS:
            ref = get_legal_reference(std.indicator)
            assert ref is not None, f"토양 지표 '{std.indicator}'에 법적 근거 누락"
            assert ref.standard_value == std.limit_value

    def test_all_standards_have_legal_basis_field(self):
        """모든 Standard 객체에 legal_basis 필드가 비어 있지 않아야 한다."""
        all_standards = AIR_STANDARDS + WATER_STANDARDS + NOISE_STANDARDS + SOIL_STANDARDS
        for std in all_standards:
            assert std.legal_basis, f"지표 '{std.indicator}'의 legal_basis가 비어 있음"

    def test_category_legal_refs_cover_all_categories(self):
        """모든 환경기준 카테고리에 법적 근거가 정의되어 있어야 한다."""
        for category in STANDARDS_BY_CATEGORY:
            ref = get_category_legal_reference(category)
            assert ref is not None, f"카테고리 '{category}'에 법적 근거 누락"
            assert ref.law_name, f"카테고리 '{category}' 법률명 누락"
            assert ref.article, f"카테고리 '{category}' 조문 누락"

    def test_legal_reference_fields_nonempty(self):
        """모든 법적 근거 항목의 필수 필드가 채워져 있어야 한다."""
        for indicator, ref in ALL_INDICATOR_REFS.items():
            assert ref.law_name, f"'{indicator}' 법률명 누락"
            assert ref.article, f"'{indicator}' 조문 누락"
            assert ref.legal_basis, f"'{indicator}' 법적 근거 문자열 누락"
            assert ref.unit, f"'{indicator}' 단위 누락"

    def test_get_legal_reference_returns_none_for_unknown(self):
        """미등록 지표에 대해 None을 반환해야 한다."""
        assert get_legal_reference("존재하지않는지표") is None

    def test_get_category_legal_reference_returns_none_for_unknown(self):
        """미등록 카테고리에 대해 None을 반환해야 한다."""
        assert get_category_legal_reference("unknown_category") is None

    def test_air_legal_basis_content(self):
        """대기 기준의 법적 근거가 올바른 법령을 참조해야 한다."""
        ref = get_legal_reference("PM10_연평균")
        assert ref is not None
        assert "환경정책기본법" in ref.legal_basis
        assert "별표" in ref.legal_basis

    def test_soil_legal_basis_content(self):
        """토양 기준의 법적 근거가 올바른 법령을 참조해야 한다."""
        ref = get_legal_reference("Cd")
        assert ref is not None
        assert "토양환경보전법" in ref.legal_basis
        assert "별표" in ref.legal_basis

    def test_indicator_ref_count_matches_standards(self):
        """법적 근거 매핑 수가 환경기준 지표 수와 일치해야 한다."""
        # 고유 지표 수 기준 비교
        all_std_indicators = set()
        for std in AIR_STANDARDS + WATER_STANDARDS + NOISE_STANDARDS + SOIL_STANDARDS:
            all_std_indicators.add(std.indicator)
        assert len(ALL_INDICATOR_REFS) == len(all_std_indicators), (
            f"법적 근거 매핑 수({len(ALL_INDICATOR_REFS)})와 "
            f"환경기준 지표 수({len(all_std_indicators)}) 불일치"
        )


# ────────────────────────────────────────────
# 2. 사업유형별 필수 평가 항목 완전성 테스트
# ────────────────────────────────────────────


class TestRequiredItems:
    """사업유형별 필수 평가 항목 완전성 테스트."""

    # 현재 ProjectType enum에 정의된 모든 유형
    KNOWN_PROJECT_TYPES = [
        "road", "railway", "power_plant", "industrial", "housing",
        "airport", "port", "dam", "reclamation", "other",
    ]

    # 사용자 지정 추가 유형 (enum에는 없지만 규정에서 정의)
    EXTRA_TYPES = ["tourism", "military"]

    def test_all_project_types_have_requirements(self):
        """모든 사업유형에 필수 항목이 정의되어 있어야 한다."""
        for pt in self.KNOWN_PROJECT_TYPES:
            assert pt in REQUIRED_BY_TYPE, f"사업유형 '{pt}'에 필수 항목 미정의"

    def test_extra_types_have_requirements(self):
        """추가 사업유형(tourism, military)도 필수 항목이 정의되어 있어야 한다."""
        for pt in self.EXTRA_TYPES:
            assert pt in REQUIRED_BY_TYPE, f"사업유형 '{pt}'에 필수 항목 미정의"

    def test_each_type_has_nonempty_sections(self):
        """모든 사업유형의 필수 섹션 목록이 비어 있지 않아야 한다."""
        for pt, req in REQUIRED_BY_TYPE.items():
            assert len(req.required_sections) > 0, (
                f"사업유형 '{pt}'에 필수 섹션 0개"
            )

    def test_each_section_has_nonempty_indicators(self):
        """각 필수 섹션에 최소 1개 이상의 필수 지표가 있어야 한다."""
        for pt, req in REQUIRED_BY_TYPE.items():
            for sec in req.required_sections:
                assert len(sec.required_indicators) > 0, (
                    f"사업유형 '{pt}', 섹션 '{sec.section_key}'에 필수 지표 0개"
                )

    def test_military_requires_all_sections(self):
        """군사 사업유형은 전 항목이 필수여야 한다."""
        sections = get_required_sections("military")
        expected = [
            "air_quality", "water_quality", "soil", "noise_vibration",
            "ecology", "land_use", "traffic", "waste",
            "landscape", "cultural_heritage", "climate",
        ]
        for s in expected:
            assert s in sections, f"군사 사업유형에 필수 섹션 '{s}' 누락"

    def test_power_plant_required_sections(self):
        """발전소 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("power_plant")
        expected = ["air_quality", "water_quality", "noise_vibration", "ecology", "land_use"]
        for s in expected:
            assert s in sections, f"발전소 필수 섹션 '{s}' 누락"

    def test_road_required_sections(self):
        """도로 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("road")
        expected = ["air_quality", "noise_vibration", "ecology", "land_use", "traffic"]
        for s in expected:
            assert s in sections, f"도로 필수 섹션 '{s}' 누락"

    def test_housing_required_sections(self):
        """주거단지 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("housing")
        expected = ["air_quality", "water_quality", "noise_vibration", "traffic", "waste"]
        for s in expected:
            assert s in sections, f"주거단지 필수 섹션 '{s}' 누락"

    def test_industrial_required_sections(self):
        """산업단지 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("industrial")
        expected = ["air_quality", "water_quality", "soil", "noise_vibration", "waste"]
        for s in expected:
            assert s in sections, f"산업단지 필수 섹션 '{s}' 누락"

    def test_tourism_required_sections(self):
        """관광 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("tourism")
        expected = ["ecology", "landscape", "cultural_heritage", "land_use"]
        for s in expected:
            assert s in sections, f"관광 필수 섹션 '{s}' 누락"

    def test_port_required_sections(self):
        """항만 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("port")
        expected = ["water_quality", "noise_vibration", "ecology", "traffic"]
        for s in expected:
            assert s in sections, f"항만 필수 섹션 '{s}' 누락"

    def test_other_required_sections(self):
        """기타 사업유형의 필수 섹션이 올바른지 검증한다."""
        sections = get_required_sections("other")
        expected = ["air_quality", "water_quality", "noise_vibration", "land_use"]
        for s in expected:
            assert s in sections, f"기타 필수 섹션 '{s}' 누락"

    def test_unknown_type_falls_back_to_other(self):
        """미등록 사업유형은 'other' 기준으로 처리해야 한다."""
        sections = get_required_sections("unknown_project_type")
        other_sections = get_required_sections("other")
        assert sections == other_sections

    def test_get_required_indicators_returns_list(self):
        """필수 지표 조회가 리스트를 반환해야 한다."""
        indicators = get_required_indicators("power_plant", "air_quality")
        assert isinstance(indicators, list)
        assert len(indicators) > 0
        assert "PM10_연평균" in indicators

    def test_get_required_indicators_nonrequired_section(self):
        """필수가 아닌 섹션의 필수 지표 조회 시 빈 리스트를 반환해야 한다."""
        indicators = get_required_indicators("road", "soil")
        assert indicators == []

    def test_each_requirement_has_legal_basis(self):
        """모든 사업유형에 법적 근거가 기재되어 있어야 한다."""
        for pt, req in REQUIRED_BY_TYPE.items():
            assert req.legal_basis, f"사업유형 '{pt}'에 법적 근거 누락"

    def test_each_requirement_has_type_name(self):
        """모든 사업유형에 한글 유형명이 기재되어 있어야 한다."""
        for pt, req in REQUIRED_BY_TYPE.items():
            assert req.type_name, f"사업유형 '{pt}'에 유형명 누락"

    def test_get_project_type_requirement(self):
        """사업유형 전체 요건 조회가 올바르게 동작해야 한다."""
        req = get_project_type_requirement("power_plant")
        assert req is not None
        assert req.type_name == "발전소"

    def test_get_project_type_requirement_unknown(self):
        """미등록 사업유형에 대해 None을 반환해야 한다."""
        assert get_project_type_requirement("nonexistent") is None


# ────────────────────────────────────────────
# 3. 지역구분별 기준 구조 테스트
# ────────────────────────────────────────────


class TestAreaClassifications:
    """소음 지역구분별 기준 구조 테스트."""

    AREA_CODES = ["가", "나", "다", "라"]

    def test_all_area_codes_defined(self):
        """모든 지역구분 코드가 정의되어 있어야 한다."""
        for code in self.AREA_CODES:
            assert code in NOISE_AREA_STANDARDS, f"지역구분 '{code}' 미정의"

    def test_general_dict_has_all_codes(self):
        """일반지역 딕셔너리에 모든 지역구분이 있어야 한다."""
        for code in self.AREA_CODES:
            assert code in NOISE_AREA_GENERAL

    def test_roadside_dict_has_all_codes(self):
        """도로변지역 딕셔너리에 모든 지역구분이 있어야 한다."""
        for code in self.AREA_CODES:
            assert code in NOISE_AREA_ROADSIDE

    def test_each_area_has_daytime_nighttime(self):
        """각 지역에 주간/야간 기준이 모두 있어야 한다."""
        for code in self.AREA_CODES:
            general = NOISE_AREA_GENERAL[code]
            assert "주간" in general, f"'{code}' 일반지역 주간 기준 누락"
            assert "야간" in general, f"'{code}' 일반지역 야간 기준 누락"
            roadside = NOISE_AREA_ROADSIDE[code]
            assert "주간" in roadside, f"'{code}' 도로변 주간 기준 누락"
            assert "야간" in roadside, f"'{code}' 도로변 야간 기준 누락"

    def test_가_area_values(self):
        """'가' 지역 기준값이 올바른지 검증한다."""
        assert NOISE_AREA_GENERAL["가"]["주간"] == 50.0
        assert NOISE_AREA_GENERAL["가"]["야간"] == 40.0
        assert NOISE_AREA_ROADSIDE["가"]["주간"] == 55.0
        assert NOISE_AREA_ROADSIDE["가"]["야간"] == 45.0

    def test_나_area_values(self):
        """'나' 지역 기준값이 올바른지 검증한다."""
        assert NOISE_AREA_GENERAL["나"]["주간"] == 55.0
        assert NOISE_AREA_GENERAL["나"]["야간"] == 45.0
        assert NOISE_AREA_ROADSIDE["나"]["주간"] == 60.0
        assert NOISE_AREA_ROADSIDE["나"]["야간"] == 50.0

    def test_다_area_values(self):
        """'다' 지역 기준값이 올바른지 검증한다."""
        assert NOISE_AREA_GENERAL["다"]["주간"] == 60.0
        assert NOISE_AREA_GENERAL["다"]["야간"] == 50.0
        assert NOISE_AREA_ROADSIDE["다"]["주간"] == 65.0
        assert NOISE_AREA_ROADSIDE["다"]["야간"] == 55.0

    def test_라_area_values(self):
        """'라' 지역 기준값이 올바른지 검증한다."""
        assert NOISE_AREA_GENERAL["라"]["주간"] == 65.0
        assert NOISE_AREA_GENERAL["라"]["야간"] == 55.0
        assert NOISE_AREA_ROADSIDE["라"]["주간"] == 70.0
        assert NOISE_AREA_ROADSIDE["라"]["야간"] == 60.0

    def test_roadside_always_higher_than_general(self):
        """도로변 기준값은 항상 일반지역보다 높아야 한다."""
        for code in self.AREA_CODES:
            for period in ("주간", "야간"):
                general = NOISE_AREA_GENERAL[code][period]
                roadside = NOISE_AREA_ROADSIDE[code][period]
                assert roadside > general, (
                    f"'{code}' {period}: 도로변({roadside}) ≤ 일반({general})"
                )

    def test_daytime_always_higher_than_nighttime(self):
        """주간 기준값은 항상 야간보다 높아야 한다."""
        for code in self.AREA_CODES:
            assert NOISE_AREA_GENERAL[code]["주간"] > NOISE_AREA_GENERAL[code]["야간"]
            assert NOISE_AREA_ROADSIDE[code]["주간"] > NOISE_AREA_ROADSIDE[code]["야간"]

    def test_get_noise_standard_general(self):
        """일반지역 소음 기준값 조회가 올바르게 동작해야 한다."""
        assert get_noise_standard("가", "주간", is_roadside=False) == 50.0
        assert get_noise_standard("라", "야간", is_roadside=False) == 55.0

    def test_get_noise_standard_roadside(self):
        """도로변 소음 기준값 조회가 올바르게 동작해야 한다."""
        assert get_noise_standard("가", "주간", is_roadside=True) == 55.0
        assert get_noise_standard("라", "야간", is_roadside=True) == 60.0

    def test_get_noise_standard_unknown_area(self):
        """미등록 지역 코드에 대해 None을 반환해야 한다."""
        assert get_noise_standard("마", "주간") is None

    def test_get_noise_standard_unknown_period(self):
        """미등록 시간대에 대해 None을 반환해야 한다."""
        assert get_noise_standard("가", "새벽") is None

    def test_get_noise_area_info(self):
        """소음 지역구분 전체 정보 조회가 올바르게 동작해야 한다."""
        info = get_noise_area_info("가")
        assert info is not None
        assert info.area_code == "가"
        assert "주거" in info.applicable_zones

    def test_get_noise_area_info_unknown(self):
        """미등록 지역 코드에 대해 None을 반환해야 한다."""
        assert get_noise_area_info("마") is None


# ────────────────────────────────────────────
# 4. env_standards.py 하위 호환성 테스트
# ────────────────────────────────────────────


class TestEnvStandardsCompat:
    """env_standards.py의 legal_basis 추가 후 하위 호환성 테스트."""

    def test_standard_has_legal_basis_attribute(self):
        """Standard 데이터클래스에 legal_basis 속성이 존재해야 한다."""
        std = AIR_STANDARDS[0]
        assert hasattr(std, "legal_basis")

    def test_existing_fields_unchanged(self):
        """기존 필드(indicator, time_basis, limit_value 등)가 유지되어야 한다."""
        std = AIR_STANDARDS[0]  # PM10_연평균
        assert std.indicator == "PM10_연평균"
        assert std.time_basis == "연평균"
        assert std.limit_value == 50.0
        assert std.unit == "ug/m3"

    def test_get_standard_for_indicator_still_works(self):
        """기존 get_standard_for_indicator 함수가 정상 동작해야 한다."""
        std = get_standard_for_indicator("air_quality", "PM10_연평균")
        assert std is not None
        assert std.limit_value == 50.0

    def test_get_standards_for_category_still_works(self):
        """기존 get_standards_for_category 함수가 정상 동작해야 한다."""
        stds = get_standards_for_category("water_quality")
        assert len(stds) == 6  # BOD, COD, SS, DO, T-P, T-N

    def test_legal_basis_default_empty_for_manual_standard(self):
        """legal_basis 미지정 시 빈 문자열이 기본값이어야 한다."""
        std = Standard("test", "평균", 1.0, "unit", "leq")
        assert std.legal_basis == ""

    def test_water_grades_unchanged(self):
        """수질 등급 구조는 변경되지 않아야 한다."""
        from app.data.env_standards import WATER_GRADES, determine_water_grade
        assert len(WATER_GRADES) == 6
        grade = determine_water_grade(bod=1.5)
        assert grade is not None
        assert grade.grade == "Ib"


# ────────────────────────────────────────────
# 5. QA 규칙 R007/R008 법적 필수 항목 검증 테스트
# ────────────────────────────────────────────

from app.services.qa_engine import (
    Severity,
    QaIssue,
    _get_critical_sections,
    _get_project_type_name,
    _rule_required_section_missing,
    _rule_required_indicator_missing,
    _rule_section_empty,
)
from app.services.section_planner import (
    SectionDefinition,
    IndicatorStatus,
    SectionStatus,
)


def _make_section_def(key: str, title: str, indicators: list[str]) -> SectionDefinition:
    """테스트용 SectionDefinition 생성."""
    return SectionDefinition(
        key=key,
        title=title,
        description=f"{title} 설명",
        evidence_category=key,
        required_indicators=indicators,
        order=1,
    )


def _make_section_status(
    key: str,
    title: str,
    total_evidence: int = 0,
    indicators: list[tuple[str, bool, int]] | None = None,
) -> SectionStatus:
    """테스트용 SectionStatus 생성.

    indicators: [(이름, 충족여부, evidence_count), ...]
    """
    ind_list = []
    fulfilled = 0
    missing = []
    if indicators:
        for name, is_fulfilled, count in indicators:
            ind_list.append(IndicatorStatus(name=name, fulfilled=is_fulfilled, evidence_count=count))
            if is_fulfilled:
                fulfilled += 1
            else:
                missing.append(name)
    required_count = len(ind_list)
    ratio = fulfilled / required_count if required_count > 0 else 0.0
    if total_evidence == 0:
        status = "empty"
    elif fulfilled >= required_count:
        status = "complete"
    else:
        status = "partial"
    return SectionStatus(
        section_key=key,
        title=title,
        description=f"{title} 설명",
        order=1,
        total_evidence_count=total_evidence,
        required_indicators=ind_list,
        fulfilled_count=fulfilled,
        required_count=required_count,
        coverage_ratio=round(ratio, 4),
        status=status,
        missing_indicators=missing,
    )


class TestR007RequiredSectionMissing:
    """R007: 법적 필수 섹션 누락 테스트."""

    def test_power_plant_empty_air_quality_triggers_r007(self):
        """발전소 사업에서 대기질 섹션 비어 있으면 R007 critical이 발생해야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균", "PM2.5_연평균"])
        sec_status = _make_section_status("air_quality", "대기질", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "power_plant")
        assert issue is not None
        assert issue.rule_id == "R007"
        assert issue.severity == Severity.CRITICAL
        assert "발전소" in issue.message
        assert "대기질" in issue.message
        assert "환경영향평가법 시행령 별표 3" in issue.legal_basis

    def test_power_plant_with_data_no_r007(self):
        """발전소 사업에서 대기질 데이터가 있으면 R007이 발생하지 않아야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균"])
        sec_status = _make_section_status(
            "air_quality", "대기질", total_evidence=3,
            indicators=[("PM10_연평균", True, 3)],
        )
        issue = _rule_required_section_missing(sec_def, sec_status, "power_plant")
        assert issue is None

    def test_tourism_empty_air_quality_no_r007(self):
        """관광 사업에서 대기질은 필수가 아니므로 R007이 발생하지 않아야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균"])
        sec_status = _make_section_status("air_quality", "대기질", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "tourism")
        assert issue is None

    def test_tourism_empty_ecology_triggers_r007(self):
        """관광 사업에서 생태 섹션 비어 있으면 R007이 발생해야 한다."""
        sec_def = _make_section_def("ecology", "생태", ["식물상_종수", "동물상_종수"])
        sec_status = _make_section_status("ecology", "생태", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "tourism")
        assert issue is not None
        assert issue.rule_id == "R007"
        assert issue.severity == Severity.CRITICAL
        assert "관광" in issue.message

    def test_road_empty_traffic_triggers_r007(self):
        """도로 사업에서 교통 섹션 비어 있으면 R007이 발생해야 한다."""
        sec_def = _make_section_def("traffic", "교통", ["교통량_현황"])
        sec_status = _make_section_status("traffic", "교통", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "road")
        assert issue is not None
        assert issue.rule_id == "R007"
        assert "도로" in issue.message

    def test_unknown_project_type_uses_other_fallback(self):
        """미등록 사업유형은 'other' 기준을 적용한다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균"])
        sec_status = _make_section_status("air_quality", "대기질", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "unknown_type")
        # 'other' 타입에서 air_quality는 필수
        assert issue is not None
        assert issue.rule_id == "R007"

    def test_r007_legal_basis_field_nonempty(self):
        """R007 이슈에는 항상 법적 근거가 포함되어야 한다."""
        sec_def = _make_section_def("water_quality", "수질", ["BOD"])
        sec_status = _make_section_status("water_quality", "수질", total_evidence=0)
        issue = _rule_required_section_missing(sec_def, sec_status, "industrial")
        assert issue is not None
        assert issue.legal_basis != ""
        assert "별표 3" in issue.legal_basis


class TestR008RequiredIndicatorMissing:
    """R008: 법적 필수 지표 누락 테스트."""

    def test_power_plant_missing_air_indicator_triggers_r008(self):
        """발전소 사업에서 대기질 필수 지표 누락 시 R008이 발생해야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", [
            "PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균",
        ])
        sec_status = _make_section_status(
            "air_quality", "대기질", total_evidence=2,
            indicators=[
                ("PM10_연평균", True, 1),
                ("PM2.5_연평균", True, 1),
                ("NO2_연평균", False, 0),
                ("SO2_연평균", False, 0),
            ],
        )
        issues = _rule_required_indicator_missing(sec_def, sec_status, "power_plant")
        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule_id == "R008"
        assert issue.severity == Severity.WARNING
        assert "NO2_연평균" in issue.message
        assert "SO2_연평균" in issue.message
        assert issue.legal_basis != ""

    def test_power_plant_all_indicators_present_no_r008(self):
        """발전소 사업에서 모든 법적 필수 지표가 있으면 R008이 발생하지 않아야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", [
            "PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균",
        ])
        sec_status = _make_section_status(
            "air_quality", "대기질", total_evidence=4,
            indicators=[
                ("PM10_연평균", True, 1),
                ("PM2.5_연평균", True, 1),
                ("NO2_연평균", True, 1),
                ("SO2_연평균", True, 1),
            ],
        )
        issues = _rule_required_indicator_missing(sec_def, sec_status, "power_plant")
        assert len(issues) == 0

    def test_empty_section_no_r008(self):
        """섹션에 증거가 전혀 없으면 R008이 아닌 R007에서 처리된다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균"])
        sec_status = _make_section_status("air_quality", "대기질", total_evidence=0)
        issues = _rule_required_indicator_missing(sec_def, sec_status, "power_plant")
        assert len(issues) == 0

    def test_non_required_section_no_r008(self):
        """필수가 아닌 섹션에서는 R008이 발생하지 않아야 한다."""
        sec_def = _make_section_def("landscape", "경관", ["주요_조망점"])
        sec_status = _make_section_status(
            "landscape", "경관", total_evidence=1,
            indicators=[("주요_조망점", False, 0)],
        )
        # power_plant에서 landscape는 필수가 아님
        issues = _rule_required_indicator_missing(sec_def, sec_status, "power_plant")
        assert len(issues) == 0

    def test_r008_indicators_match_missing(self):
        """R008의 indicators 필드에 누락된 법적 필수 지표만 포함되어야 한다."""
        sec_def = _make_section_def("water_quality", "수질", [
            "BOD", "COD", "SS", "DO", "T-P", "T-N",
        ])
        sec_status = _make_section_status(
            "water_quality", "수질", total_evidence=3,
            indicators=[
                ("BOD", True, 1),
                ("COD", True, 1),
                ("SS", True, 1),
                ("DO", False, 0),
                ("T-P", False, 0),
                ("T-N", False, 0),
            ],
        )
        issues = _rule_required_indicator_missing(sec_def, sec_status, "power_plant")
        assert len(issues) == 1
        issue = issues[0]
        # power_plant 수질 필수: BOD, COD, SS, DO, T-P
        # T-N은 power_plant 법적 필수가 아님
        assert "DO" in issue.indicators
        assert "T-P" in issue.indicators
        assert "T-N" not in issue.indicators


class TestR001DynamicCritical:
    """R001: 사업유형 기반 동적 심각도 판단 테스트."""

    def test_critical_sections_with_project_type(self):
        """사업유형 설정 시 필수 섹션이 동적으로 결정되어야 한다."""
        # power_plant: air_quality, water_quality, noise_vibration, ecology, land_use
        cs = _get_critical_sections("power_plant")
        assert "air_quality" in cs
        assert "water_quality" in cs
        assert "ecology" in cs
        assert "land_use" in cs
        # traffic은 power_plant 필수가 아님
        assert "traffic" not in cs

    def test_critical_sections_without_project_type(self):
        """사업유형 미설정 시 기존 하드코딩 fallback을 사용해야 한다."""
        cs = _get_critical_sections(None)
        assert cs == {"air_quality", "water_quality", "noise_vibration", "ecology"}

    def test_r001_skips_legally_required_sections(self):
        """법적 필수 섹션은 R007에서 처리하므로 R001이 건너뛰어야 한다."""
        sec_def = _make_section_def("air_quality", "대기질", ["PM10_연평균"])
        sec_status = _make_section_status("air_quality", "대기질", total_evidence=0)
        critical_sections = _get_critical_sections("power_plant")
        # legally_required=True → R001 발생하지 않음
        issue = _rule_section_empty(
            sec_def, sec_status, critical_sections, legally_required=True
        )
        assert issue is None

    def test_r001_fires_for_non_required_section(self):
        """법적 필수가 아닌 섹션은 R001에서 처리해야 한다."""
        sec_def = _make_section_def("landscape", "경관", ["주요_조망점"])
        sec_status = _make_section_status("landscape", "경관", total_evidence=0)
        # power_plant에서 landscape는 필수가 아님
        critical_sections = _get_critical_sections("power_plant")
        issue = _rule_section_empty(
            sec_def, sec_status, critical_sections, legally_required=False
        )
        assert issue is not None
        assert issue.rule_id == "R001"
        assert issue.severity == Severity.WARNING  # 필수 섹션이 아니므로 warning

    def test_r001_critical_for_tourism_ecology(self):
        """사업유형 동적 판단: 관광 사업에서 ecology 비어 있고 legally_required=False면 critical."""
        sec_def = _make_section_def("ecology", "생태", ["식물상_종수"])
        sec_status = _make_section_status("ecology", "생태", total_evidence=0)
        # 관광: ecology는 필수 → critical_sections에 포함
        critical_sections = _get_critical_sections("tourism")
        assert "ecology" in critical_sections
        # legally_required=False로 설정 시 R001이 critical로 동작
        issue = _rule_section_empty(
            sec_def, sec_status, critical_sections, legally_required=False
        )
        assert issue is not None
        assert issue.severity == Severity.CRITICAL


class TestQaIssurLegalBasis:
    """QaIssue legal_basis 필드 테스트."""

    def test_qa_issue_default_legal_basis_empty(self):
        """QaIssue의 legal_basis 기본값은 빈 문자열이어야 한다."""
        issue = QaIssue(
            rule_id="R001", severity=Severity.WARNING,
            section_key="air_quality", title="테스트", message="메시지",
        )
        assert issue.legal_basis == ""

    def test_qa_issue_with_legal_basis(self):
        """QaIssue에 legal_basis를 설정할 수 있어야 한다."""
        issue = QaIssue(
            rule_id="R007", severity=Severity.CRITICAL,
            section_key="air_quality", title="테스트", message="메시지",
            legal_basis="환경영향평가법 시행령 별표 3",
        )
        assert issue.legal_basis == "환경영향평가법 시행령 별표 3"

    def test_project_type_name_lookup(self):
        """사업유형 코드가 한글명으로 올바르게 변환되어야 한다."""
        assert _get_project_type_name("power_plant") == "발전소"
        assert _get_project_type_name("road") == "도로"
        assert _get_project_type_name("tourism") == "관광"
        assert _get_project_type_name("military") == "군사"

    def test_unknown_project_type_name_passthrough(self):
        """미등록 사업유형 코드는 그대로 반환되어야 한다."""
        assert _get_project_type_name("custom_type") == "custom_type"


class TestQaExportLegalBasisColumn:
    """부록 C QA 결과 테이블에 법적 근거 열 반영 테스트."""

    def test_docx_appendix_c_has_legal_basis_column(self):
        """DOCX 부록 C 테이블에 '법적 근거' 열이 있어야 한다."""
        from app.services.export_service import _build_docx, ExportContext, ExportOptions
        from app.services.qa_engine import QaResult, QaSummary
        from app.services.draft_scaffold import DraftScaffold, ScaffoldSection, EvidenceEntry

        scaffold = DraftScaffold(
            project_id="test-id",
            generated_at="2025-06-01T00:00:00",
            sections=[],
            total_evidence_count=0,
        )
        qa_issue = QaIssue(
            rule_id="R007", severity=Severity.CRITICAL,
            section_key="air_quality", title="대기질 법적 필수 섹션 누락",
            message="발전소 사업은 환경영향평가법 시행령 별표 3에 따라 대기질 평가가 필수입니다.",
            legal_basis="환경영향평가법 시행령 별표 3",
        )
        qa_result = QaResult(
            project_id="test-id",
            run_at="2025-06-01T00:00:00",
            issues=[qa_issue],
            summary=QaSummary(critical_count=1, warning_count=0, info_count=0),
            export_ready=False,
        )
        ctx = ExportContext(
            scaffold=scaffold,
            project_name="테스트",
            project_type="power_plant",
            centroid=None,
            section_data={},
            similar_cases=[],
            qa_result=qa_result,
            options=ExportOptions(
                include_appendix_a=False,
                include_appendix_b=False,
                include_appendix_c=True,
            ),
            generated_at="2025-06-01T00:00:00",
        )
        doc = _build_docx(ctx)
        # 부록 C 테이블 찾기 — 마지막 테이블이 QA 결과
        last_table = doc.tables[-1]
        header_row = last_table.rows[0]
        header_texts = [cell.text for cell in header_row.cells]
        assert "법적 근거" in header_texts
        # 데이터 행에 법적 근거 값이 있어야 함
        data_row = last_table.rows[1]
        data_texts = [cell.text for cell in data_row.cells]
        assert "환경영향평가법 시행령 별표 3" in data_texts
