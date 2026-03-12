"""섹션 플래너 및 초안 뼈대 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ────────────────────────────────────────────
# 섹션 상태 스키마
# ────────────────────────────────────────────

class SectionStatusEnum(str, Enum):
    """섹션 상태.

    기본 3종(empty/partial/complete)은 증거 충족도 기반으로 자동 계산된다.
    확장 4종(auto_filled/evidence_draft/expert_required/not_applicable)은
    output-contracts.md 스펙에 따른 의미론적 상태이다.
    """

    # 기본 충족도 기반 상태
    EMPTY = "empty"                       # 증거 0건
    PARTIAL = "partial"                   # 일부 지표 충족
    COMPLETE = "complete"                 # 전체 지표 충족

    # 확장 의미론적 상태 (output-contracts.md 스펙)
    AUTO_FILLED = "auto_filled"           # complete이면서 모든 evidence가 자동 수집(snapshot_id 있음)
    EVIDENCE_DRAFT = "evidence_draft"     # 증거는 있으나 초안 텍스트 미생성 상태
    EXPERT_REQUIRED = "expert_required"   # 전문가 판단 필요 (향후 플래그로 표시)
    NOT_APPLICABLE = "not_applicable"     # 해당 섹션 해당 없음 (사용자 수동 설정)


class IndicatorStatusRead(BaseModel):
    """개별 지표 충족 상태."""

    name: str = Field(..., description="지표명")
    fulfilled: bool = Field(..., description="충족 여부")
    evidence_count: int = Field(..., description="해당 지표 증거 수")


class SectionDefinitionRead(BaseModel):
    """섹션 정의 정보."""

    key: str = Field(..., description="섹션 고유 키")
    title: str = Field(..., description="섹션 제목")
    description: str = Field(..., description="섹션 설명")
    evidence_category: str = Field(..., description="대응 증거 카테고리")
    required_indicators: list[str] = Field(..., description="필수 지표 목록")
    order: int = Field(..., description="표시 순서")


class SectionStatusRead(BaseModel):
    """섹션별 증거 충족 상태 응답."""

    section_key: str
    title: str
    description: str
    order: int
    total_evidence_count: int = Field(..., description="전체 증거 수")
    required_indicators: list[IndicatorStatusRead] = Field(
        ..., description="필수 지표 충족 현황"
    )
    fulfilled_count: int = Field(..., description="충족된 필수 지표 수")
    required_count: int = Field(..., description="전체 필수 지표 수")
    coverage_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="충족도 (0.0~1.0)"
    )
    status: SectionStatusEnum = Field(..., description="섹션 상태")
    # 확장 상태 필드 (output-contracts.md 스펙 정렬)
    auto_filled: bool = Field(
        False, description="자동 수집 데이터만으로 충족 (complete + 모든 evidence에 snapshot_id 있음)"
    )
    missing_indicators: list[str] = Field(
        default_factory=list, description="누락된 필수 지표명 목록"
    )


class SectionStatusList(BaseModel):
    """프로젝트 전체 섹션 상태 목록."""

    project_id: str
    sections: list[SectionStatusRead]
    total_sections: int


# ────────────────────────────────────────────
# 초안 뼈대 스키마
# ────────────────────────────────────────────

class EvidenceEntryRead(BaseModel):
    """초안 뼈대에 배치된 개별 근거 항목."""

    evidence_id: str
    indicator: str = Field(..., description="지표명")
    value: str = Field(..., description="측정값")
    numeric_value: float | None = Field(None, description="수치형 값")
    unit: str | None = Field(None, description="단위")
    observed_at: str | None = Field(None, description="관측 시점 (ISO)")
    data_source_id: str | None = Field(None, description="데이터 소스 ID")
    metadata_json: dict | None = Field(None, description="추가 메타데이터")


class ScaffoldSectionRead(BaseModel):
    """초안 뼈대 섹션."""

    section_key: str
    title: str
    description: str
    order: int
    evidence_entries: list[EvidenceEntryRead] = Field(
        ..., description="배치된 근거 항목 목록"
    )
    summary_text: str = Field(
        ..., description="evidence 기반 자동 생성 근거 요약문 (LLM 작문 아님)"
    )
    state: SectionStatusEnum = Field(
        SectionStatusEnum.EMPTY, description="섹션 상태 (output-contracts.md 스펙)"
    )
    missing_indicators: list[str] = Field(
        default_factory=list, description="누락된 필수 지표명 목록"
    )


class DraftScaffoldRead(BaseModel):
    """초안 뼈대 전체 응답."""

    project_id: str
    generated_at: str = Field(..., description="생성 시각 (ISO)")
    sections: list[ScaffoldSectionRead]
    total_evidence_count: int = Field(..., description="전체 근거 항목 수")
