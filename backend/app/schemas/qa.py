"""QA 규칙 엔진 Pydantic 스키마."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QaSeverity(str, Enum):
    """QA 이슈 심각도."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class QaIssueRead(BaseModel):
    """단일 QA 이슈 응답."""

    rule_id: str = Field(..., description="규칙 ID (예: R001)")
    severity: QaSeverity = Field(..., description="심각도")
    section_key: str | None = Field(None, description="관련 섹션 키")
    title: str = Field(..., description="이슈 제목")
    message: str = Field(..., description="상세 설명")
    indicators: list[str] = Field(
        default_factory=list, description="관련 지표 목록"
    )


class QaSummaryRead(BaseModel):
    """QA 결과 요약 통계."""

    critical_count: int = Field(..., description="critical 이슈 수")
    warning_count: int = Field(..., description="warning 이슈 수")
    info_count: int = Field(..., description="info 이슈 수")
    total: int = Field(..., description="전체 이슈 수")


class QaResultRead(BaseModel):
    """QA 실행 결과 전체 응답."""

    project_id: str
    run_at: str = Field(..., description="실행 시각 (ISO)")
    issues: list[QaIssueRead] = Field(..., description="이슈 목록")
    summary: QaSummaryRead = Field(..., description="요약 통계")
    export_ready: bool = Field(
        ..., description="export 가능 여부 (critical 이슈 없으면 True)"
    )


class ExportReadyRead(BaseModel):
    """export 가능 여부 간략 응답."""

    project_id: str
    export_ready: bool = Field(
        ..., description="export 가능 여부"
    )
    critical_count: int = Field(
        ..., description="차단 사유인 critical 이슈 수"
    )
    message: str = Field(..., description="상태 메시지")
