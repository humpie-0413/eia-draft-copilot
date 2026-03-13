"""사업유형별 평가 범위 자동 판단 서비스.

프로젝트의 사업유형(project_type)을 기반으로
필수/권장/선택 섹션을 분류하고, 각 필수 섹션의 필수 지표 목록을 반환한다.

참조 데이터: backend/app/data/regulations/required_items.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.data.regulations.required_items import (
    REQUIRED_BY_TYPE,
    get_required_indicators,
    get_required_sections,
)
from app.services.section_planner import EIA_SECTIONS


# ────────────────────────────────────────────
# 데이터 구조
# ────────────────────────────────────────────

@dataclass(frozen=True)
class SectionScope:
    """개별 섹션의 평가 범위 분류."""

    section_key: str
    title: str
    scope: str                        # "required" | "recommended" | "optional"
    required_indicators: list[str]    # 법적 필수 지표 (required인 경우에만 값이 있음)
    legal_basis: str = ""             # 법적 근거


@dataclass(frozen=True)
class AssessmentScope:
    """프로젝트의 전체 평가 범위."""

    project_type: str
    type_name: str
    legal_basis: str
    sections: list[SectionScope]
    required_count: int = 0
    recommended_count: int = 0
    optional_count: int = 0


# ────────────────────────────────────────────
# 권장 섹션 정의 (필수는 아니지만 일반적으로 포함하는 섹션)
# ────────────────────────────────────────────

# 사업유형과 무관하게 일반적으로 권장되는 섹션
_RECOMMENDED_SECTIONS: set[str] = {
    "climate",
    "landscape",
}


def get_assessment_scope(project_type: str) -> AssessmentScope:
    """사업유형 기반 평가 범위를 계산하여 반환한다.

    분류 기준:
    - required: required_items.py에 정의된 필수 섹션
    - recommended: 필수는 아니지만 일반적으로 권장되는 섹션
    - optional: 그 외 섹션
    """
    req = REQUIRED_BY_TYPE.get(project_type)
    if req is None:
        req = REQUIRED_BY_TYPE["other"]

    required_keys = set(get_required_sections(project_type))
    all_section_keys = {s.key for s in EIA_SECTIONS}

    sections: list[SectionScope] = []
    required_count = 0
    recommended_count = 0
    optional_count = 0

    for section_def in EIA_SECTIONS:
        key = section_def.key

        if key in required_keys:
            indicators = get_required_indicators(project_type, key)
            scope = "required"
            required_count += 1
        elif key in _RECOMMENDED_SECTIONS:
            indicators = []
            scope = "recommended"
            recommended_count += 1
        else:
            indicators = []
            scope = "optional"
            optional_count += 1

        sections.append(SectionScope(
            section_key=key,
            title=section_def.title,
            scope=scope,
            required_indicators=indicators,
            legal_basis=req.legal_basis if scope == "required" else "",
        ))

    return AssessmentScope(
        project_type=req.project_type,
        type_name=req.type_name,
        legal_basis=req.legal_basis,
        sections=sections,
        required_count=required_count,
        recommended_count=recommended_count,
        optional_count=optional_count,
    )
