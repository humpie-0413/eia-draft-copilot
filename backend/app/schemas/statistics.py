"""통계 API 응답 Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndicatorStatsRead(BaseModel):
    """지표별 기술 통계 응답."""

    indicator: str = Field(..., description="지표명")
    count: int = Field(0, description="데이터 건수")
    mean: float | None = Field(None, description="평균")
    max_value: float | None = Field(None, description="최대값")
    min_value: float | None = Field(None, description="최소값")
    std_dev: float | None = Field(None, description="표준편차")
    unit: str | None = Field(None, description="단위")
    period_start: str | None = Field(None, description="최초 관측일 (ISO)")
    period_end: str | None = Field(None, description="최종 관측일 (ISO)")


class SectionStatsRead(BaseModel):
    """섹션별 통계 요약 응답."""

    section_key: str = Field(..., description="섹션 키")
    title: str = Field(..., description="섹션 제목")
    total_numeric_count: int = Field(0, description="수치 데이터 총 건수")
    indicator_stats: list[IndicatorStatsRead] = Field(
        default_factory=list, description="지표별 통계 목록"
    )
    years_filter_applied: int | None = Field(
        None, description="적용된 연도 필터 (None이면 전체 기간)"
    )


class ProjectStatsRead(BaseModel):
    """프로젝트 전체 통계 응답."""

    project_id: str
    generated_at: str = Field(..., description="생성 시각 (ISO)")
    sections: list[SectionStatsRead]
    total_numeric_count: int = Field(0, description="전체 수치 데이터 건수")
