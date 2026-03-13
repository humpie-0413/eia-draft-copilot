"""사업유형별 필수 평가 항목.

환경영향평가법 시행령 별표 3을 기반으로 사업유형별 필수 평가 항목을 정의한다.
각 사업유형에 대해 필수 섹션 키 목록과 섹션별 필수 지표를 관리한다.

참조 법령:
- 환경영향평가법 시행령 별표 3 (환경영향평가 항목 등의 결정 기준)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequiredSection:
    """사업유형별 필수 섹션 정의."""

    section_key: str                     # 섹션 키 (section_planner의 key와 일치)
    required_indicators: list[str]       # 해당 섹션에서 법적으로 필수인 지표 목록


@dataclass(frozen=True)
class ProjectTypeRequirement:
    """사업유형별 평가 요건."""

    project_type: str                             # 사업유형 코드
    type_name: str                                # 사업유형 한글명
    legal_basis: str                              # 법적 근거
    required_sections: list[RequiredSection]       # 필수 평가 섹션 및 지표


# ────────────────────────────────────────────
# 사업유형별 필수 평가 항목 정의
# ────────────────────────────────────────────

# 모든 섹션 키 목록 (military 등 전 항목 필수 시 사용)
_ALL_SECTION_KEYS = [
    "air_quality", "water_quality", "soil", "noise_vibration",
    "ecology", "land_use", "traffic", "waste",
    "landscape", "cultural_heritage", "climate",
]

_LEGAL_BASIS = "환경영향평가법 시행령 별표 3"

REQUIRED_BY_TYPE: dict[str, ProjectTypeRequirement] = {
    # 발전소
    "power_plant": ProjectTypeRequirement(
        project_type="power_plant",
        type_name="발전소",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균",
            ]),
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO", "T-P",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
        ],
    ),
    # 도로
    "road": ProjectTypeRequirement(
        project_type="road",
        type_name="도로",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
            RequiredSection("traffic", [
                "교통량_현황", "서비스수준",
            ]),
        ],
    ),
    # 주거단지
    "housing": ProjectTypeRequirement(
        project_type="housing",
        type_name="주거단지",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            ]),
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("traffic", [
                "교통량_현황", "서비스수준",
            ]),
            RequiredSection("waste", [
                "폐기물_발생량", "폐기물_종류",
            ]),
        ],
    ),
    # 산업단지
    "industrial": ProjectTypeRequirement(
        project_type="industrial",
        type_name="산업단지",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균",
            ]),
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO", "T-P",
            ]),
            RequiredSection("soil", [
                "Pb", "Cd",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("waste", [
                "폐기물_발생량", "폐기물_종류",
            ]),
        ],
    ),
    # 관광
    "tourism": ProjectTypeRequirement(
        project_type="tourism",
        type_name="관광",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("landscape", [
                "주요_조망점", "경관_유형",
            ]),
            RequiredSection("cultural_heritage", [
                "문화재명", "이격거리",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
        ],
    ),
    # 항만
    "port": ProjectTypeRequirement(
        project_type="port",
        type_name="항만",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수",
            ]),
            RequiredSection("traffic", [
                "교통량_현황",
            ]),
        ],
    ),
    # 군사
    "military": ProjectTypeRequirement(
        project_type="military",
        type_name="군사",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균",
            ]),
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO", "T-P",
            ]),
            RequiredSection("soil", [
                "Pb", "Cd",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
            RequiredSection("traffic", [
                "교통량_현황",
            ]),
            RequiredSection("waste", [
                "폐기물_발생량",
            ]),
            RequiredSection("landscape", [
                "주요_조망점",
            ]),
            RequiredSection("cultural_heritage", [
                "문화재명",
            ]),
            RequiredSection("climate", [
                "평균기온", "강수량",
            ]),
        ],
    ),
    # 철도
    "railway": ProjectTypeRequirement(
        project_type="railway",
        type_name="철도",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
            RequiredSection("traffic", [
                "교통량_현황",
            ]),
        ],
    ),
    # 공항
    "airport": ProjectTypeRequirement(
        project_type="airport",
        type_name="공항",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
            RequiredSection("traffic", [
                "교통량_현황",
            ]),
        ],
    ),
    # 댐
    "dam": ProjectTypeRequirement(
        project_type="dam",
        type_name="댐",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO", "T-P",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수", "법정보호종",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
        ],
    ),
    # 매립
    "reclamation": ProjectTypeRequirement(
        project_type="reclamation",
        type_name="매립",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO",
            ]),
            RequiredSection("ecology", [
                "식물상_종수", "동물상_종수",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
        ],
    ),
    # 기타
    "other": ProjectTypeRequirement(
        project_type="other",
        type_name="기타",
        legal_basis=_LEGAL_BASIS,
        required_sections=[
            RequiredSection("air_quality", [
                "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            ]),
            RequiredSection("water_quality", [
                "BOD", "COD", "SS", "DO",
            ]),
            RequiredSection("noise_vibration", [
                "소음_Leq_주간", "소음_Leq_야간",
            ]),
            RequiredSection("land_use", [
                "용도지역구분", "지목",
            ]),
        ],
    ),
}


def get_required_sections(project_type: str) -> list[str]:
    """사업유형의 필수 섹션 키 목록을 반환한다.

    미등록 사업유형이면 'other' 기준을 적용한다.
    """
    req = REQUIRED_BY_TYPE.get(project_type)
    if req is None:
        req = REQUIRED_BY_TYPE["other"]
    return [s.section_key for s in req.required_sections]


def get_required_indicators(project_type: str, section_key: str) -> list[str]:
    """사업유형 + 섹션의 필수 지표 목록을 반환한다.

    해당 섹션이 필수가 아니면 빈 리스트를 반환한다.
    """
    req = REQUIRED_BY_TYPE.get(project_type)
    if req is None:
        req = REQUIRED_BY_TYPE["other"]
    for s in req.required_sections:
        if s.section_key == section_key:
            return list(s.required_indicators)
    return []


def get_project_type_requirement(
    project_type: str,
) -> ProjectTypeRequirement | None:
    """사업유형의 전체 평가 요건을 반환한다."""
    return REQUIRED_BY_TYPE.get(project_type)
