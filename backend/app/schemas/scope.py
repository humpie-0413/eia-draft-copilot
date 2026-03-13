"""평가 범위 Pydantic 스키마."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SectionScopeEnum(str, Enum):
    """섹션 평가 범위 분류."""

    REQUIRED = "required"           # 법적 필수
    RECOMMENDED = "recommended"     # 권장
    OPTIONAL = "optional"           # 선택


class SectionScopeRead(BaseModel):
    """개별 섹션의 평가 범위."""

    section_key: str = Field(..., description="섹션 키")
    title: str = Field(..., description="섹션 제목")
    scope: SectionScopeEnum = Field(..., description="범위 분류")
    required_indicators: list[str] = Field(
        default_factory=list, description="법적 필수 지표 목록"
    )
    legal_basis: str = Field("", description="법적 근거")


class AssessmentScopeRead(BaseModel):
    """프로젝트 전체 평가 범위 응답."""

    project_type: str = Field(..., description="사업유형 코드")
    type_name: str = Field(..., description="사업유형 한글명")
    legal_basis: str = Field(..., description="법적 근거")
    sections: list[SectionScopeRead] = Field(..., description="섹션별 범위")
    required_count: int = Field(..., description="필수 섹션 수")
    recommended_count: int = Field(..., description="권장 섹션 수")
    optional_count: int = Field(..., description="선택 섹션 수")
