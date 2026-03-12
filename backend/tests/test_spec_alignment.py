"""Post-0.5: output-contracts.md 스펙 정렬 테스트.

섹션 상태 확장, category↔medium 매핑, scaffold 응답 변경을 검증한다.
"""

import pytest

from app.schemas.evidence import (
    EvidenceCategory,
    category_to_medium,
    medium_to_category,
)
from app.schemas.section import SectionStatusEnum


# ────────────────────────────────────────────
# category ↔ medium 매핑 테스트
# ────────────────────────────────────────────


class TestCategoryMediumMapping:
    """category_to_medium / medium_to_category 양방향 변환 테스트."""

    def test_category_to_medium_air(self):
        assert category_to_medium("air_quality") == "air"

    def test_category_to_medium_water(self):
        assert category_to_medium("water_quality") == "water"

    def test_category_to_medium_noise(self):
        assert category_to_medium("noise_vibration") == "noise"

    def test_category_to_medium_land_use(self):
        assert category_to_medium("land_use") == "landuse"

    def test_category_to_medium_passthrough(self):
        """매핑에 없는 값은 그대로 반환."""
        assert category_to_medium("ecology") == "ecology"
        assert category_to_medium("soil") == "soil"

    def test_category_to_medium_unknown(self):
        """알 수 없는 값은 그대로 반환."""
        assert category_to_medium("unknown_category") == "unknown_category"

    def test_medium_to_category_air(self):
        assert medium_to_category("air") == "air_quality"

    def test_medium_to_category_water(self):
        assert medium_to_category("water") == "water_quality"

    def test_medium_to_category_noise(self):
        assert medium_to_category("noise") == "noise_vibration"

    def test_medium_to_category_landuse(self):
        assert medium_to_category("landuse") == "land_use"

    def test_medium_to_category_unknown(self):
        """알 수 없는 값은 그대로 반환."""
        assert medium_to_category("unknown_medium") == "unknown_medium"

    def test_roundtrip_all_categories(self):
        """모든 EvidenceCategory에 대해 category→medium→category 왕복 변환 검증."""
        for cat in EvidenceCategory:
            medium = category_to_medium(cat.value)
            back = medium_to_category(medium)
            assert back == cat.value, (
                f"왕복 변환 실패: {cat.value} → {medium} → {back}"
            )


# ────────────────────────────────────────────
# 섹션 상태 Enum 테스트
# ────────────────────────────────────────────


class TestSectionStatusEnum:
    """SectionStatusEnum이 기본 3종 + 확장 4종을 포함하는지 검증."""

    def test_basic_states_exist(self):
        """기본 충족도 기반 상태 3종 존재 확인."""
        assert SectionStatusEnum.EMPTY.value == "empty"
        assert SectionStatusEnum.PARTIAL.value == "partial"
        assert SectionStatusEnum.COMPLETE.value == "complete"

    def test_extended_states_exist(self):
        """확장 의미론적 상태 4종 존재 확인."""
        assert SectionStatusEnum.AUTO_FILLED.value == "auto_filled"
        assert SectionStatusEnum.EVIDENCE_DRAFT.value == "evidence_draft"
        assert SectionStatusEnum.EXPERT_REQUIRED.value == "expert_required"
        assert SectionStatusEnum.NOT_APPLICABLE.value == "not_applicable"

    def test_total_state_count(self):
        """전체 상태 수가 7종인지 확인."""
        assert len(SectionStatusEnum) == 7

    def test_string_enum_values(self):
        """모든 상태가 문자열로 직렬화 가능한지 확인."""
        for state in SectionStatusEnum:
            assert isinstance(state.value, str)
            assert state.value == str(state.value)


# ────────────────────────────────────────────
# section_planner 단위 테스트 (DB 불필요)
# ────────────────────────────────────────────


class TestSectionDefinitions:
    """섹션 정의의 정합성 테스트."""

    def test_all_sections_have_indicators(self):
        """모든 섹션에 필수 지표가 1개 이상 있는지 확인."""
        from app.services.section_planner import EIA_SECTIONS

        for section in EIA_SECTIONS:
            assert len(section.required_indicators) > 0, (
                f"{section.key} 섹션에 필수 지표가 없습니다"
            )

    def test_section_keys_match_categories(self):
        """섹션 key와 evidence_category가 일치하는지 확인."""
        from app.services.section_planner import EIA_SECTIONS

        for section in EIA_SECTIONS:
            assert section.key == section.evidence_category, (
                f"{section.key} 섹션의 evidence_category가 불일치: "
                f"{section.evidence_category}"
            )

    def test_section_keys_are_valid_categories(self):
        """모든 섹션 key가 유효한 EvidenceCategory인지 확인."""
        from app.services.section_planner import EIA_SECTIONS

        valid_categories = {cat.value for cat in EvidenceCategory}
        for section in EIA_SECTIONS:
            assert section.key in valid_categories, (
                f"{section.key}는 유효한 EvidenceCategory가 아닙니다"
            )

    def test_section_orders_unique(self):
        """섹션 order가 고유한지 확인."""
        from app.services.section_planner import EIA_SECTIONS

        orders = [s.order for s in EIA_SECTIONS]
        assert len(orders) == len(set(orders)), "섹션 order에 중복이 있습니다"

    def test_category_medium_mapping_covers_all_sections(self):
        """모든 섹션의 category가 medium 매핑에 포함되는지 확인."""
        from app.services.section_planner import EIA_SECTIONS

        for section in EIA_SECTIONS:
            medium = category_to_medium(section.key)
            assert medium != section.key or section.key in ("ecology", "soil", "waste", "landscape", "cultural_heritage", "climate", "traffic", "other"), (
                f"{section.key} 섹션의 medium 매핑이 없습니다"
            )


# ────────────────────────────────────────────
# SectionStatus 데이터클래스 테스트
# ────────────────────────────────────────────


class TestSectionStatusDataclass:
    """SectionStatus 확장 필드 테스트."""

    def test_default_values(self):
        """기본값이 올바르게 설정되는지 확인."""
        from app.services.section_planner import SectionStatus

        status = SectionStatus(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질 현황",
            order=1,
        )
        assert status.auto_filled is False
        assert status.all_have_snapshot is False
        assert status.missing_indicators == []
        assert status.status == "empty"

    def test_auto_filled_set(self):
        """auto_filled 플래그가 설정되는지 확인."""
        from app.services.section_planner import SectionStatus

        status = SectionStatus(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질 현황",
            order=1,
            status="complete",
            auto_filled=True,
            all_have_snapshot=True,
        )
        assert status.auto_filled is True
        assert status.all_have_snapshot is True

    def test_missing_indicators(self):
        """missing_indicators 목록이 올바르게 설정되는지 확인."""
        from app.services.section_planner import SectionStatus

        missing = ["PM10_연평균", "PM2.5_연평균"]
        status = SectionStatus(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질 현황",
            order=1,
            status="partial",
            missing_indicators=missing,
        )
        assert status.missing_indicators == missing
        assert len(status.missing_indicators) == 2
