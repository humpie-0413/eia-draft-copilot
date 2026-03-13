"""법령 데이터 무결성 및 구조 테스트.

Reg-1에서 구축한 법령 데이터의 완전성과 정합성을 검증한다.
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
