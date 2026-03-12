"""환경기준 비교 API 응답 Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndicatorCheckRead(BaseModel):
    """개별 지표 기준 비교 결과."""

    indicator: str = Field(..., description="지표명")
    standard_value: float | None = Field(None, description="환경기준값")
    standard_unit: str | None = Field(None, description="기준 단위")
    time_basis: str | None = Field(None, description="시간기준")
    measured_avg: float | None = Field(None, description="측정 평균값")
    measured_max: float | None = Field(None, description="측정 최대값")
    measured_count: int = Field(0, description="측정 데이터 건수")
    status: str = Field("na", description="판정 (pass/fail/na)")
    exceedance_rate: float | None = Field(None, description="초과율 (%)")
    description: str = Field("", description="기준 설명")


class SectionCheckRead(BaseModel):
    """섹션별 기준 비교 결과."""

    section_key: str = Field(..., description="섹션 키")
    title: str = Field(..., description="섹션 제목")
    indicators: list[IndicatorCheckRead] = Field(
        default_factory=list, description="지표별 비교 결과"
    )
    water_grade: str | None = Field(None, description="수질 등급 코드")
    water_grade_name: str | None = Field(None, description="수질 등급명")
    has_exceedance: bool = Field(False, description="초과 지표 존재 여부")
    exceedance_count: int = Field(0, description="초과 지표 수")
    summary: str = Field("", description="요약 서술문")


class ProjectCheckRead(BaseModel):
    """프로젝트 전체 기준 비교 결과."""

    project_id: str
    generated_at: str = Field(..., description="생성 시각 (ISO)")
    sections: list[SectionCheckRead]
    total_exceedance_count: int = Field(0, description="전체 초과 지표 수")
