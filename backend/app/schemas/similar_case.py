"""유사사례 Pydantic 스키마."""

import uuid
from datetime import datetime
from typing import Any

from geojson_pydantic import GeometryCollection, MultiPolygon, Point, Polygon
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import EvidenceCategory

# 유사사례 위치 — Point 또는 Polygon 모두 허용
SimilarCaseGeometry = Point | Polygon | MultiPolygon | GeometryCollection


class SimilarCaseCreate(BaseModel):
    """유사사례 등록 요청."""

    name: str = Field(..., min_length=1, max_length=255, description="사례명")
    description: str | None = Field(None, description="설명")
    project_type: str = Field(..., max_length=100, description="사업 유형")
    location: SimilarCaseGeometry | None = Field(None, description="사업 위치 (GeoJSON)")
    area_sqm: float | None = Field(None, ge=0, description="사업 면적 (m²)")
    completed_at: datetime | None = Field(None, description="평가 완료 시점")
    summary: str | None = Field(None, description="평가서 요약")
    key_findings: dict[str, Any] | None = Field(None, description="주요 발견사항")
    evidence_categories: list[EvidenceCategory] | None = Field(
        None, description="해당 사례의 환경 분야 목록"
    )
    source_url: str | None = Field(None, max_length=500, description="원본 문서 URL")
    metadata_json: dict[str, Any] | None = Field(None, description="추가 메타데이터")


class SimilarCaseUpdate(BaseModel):
    """유사사례 수정 요청."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    project_type: str | None = None
    location: SimilarCaseGeometry | None = None
    area_sqm: float | None = Field(None, ge=0)
    completed_at: datetime | None = None
    summary: str | None = None
    key_findings: dict[str, Any] | None = None
    evidence_categories: list[EvidenceCategory] | None = None
    source_url: str | None = None
    metadata_json: dict[str, Any] | None = None


class SimilarCaseRead(BaseModel):
    """유사사례 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    project_type: str
    location: SimilarCaseGeometry | None = None
    area_sqm: float | None
    completed_at: datetime | None
    summary: str | None
    key_findings: dict[str, Any] | None
    evidence_categories: list[str] | None
    source_url: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class SimilarCaseList(BaseModel):
    items: list[SimilarCaseRead]
    total: int


class SimilarCaseMatchResult(BaseModel):
    """유사사례 매칭 결과 — 유사도 점수 포함."""

    similar_case: SimilarCaseRead

    # 종합 유사도 (0.0 ~ 1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0, description="종합 유사도 점수")

    # 항목별 유사도 상세
    type_score: float = Field(..., ge=0.0, le=1.0, description="사업 유형 유사도")
    location_score: float = Field(..., ge=0.0, le=1.0, description="위치 유사도")
    scale_score: float = Field(..., ge=0.0, le=1.0, description="규모 유사도")
    category_score: float = Field(..., ge=0.0, le=1.0, description="환경 분야 유사도")


class SimilarCaseMatchList(BaseModel):
    """프로젝트별 유사사례 매칭 결과 목록."""

    project_id: uuid.UUID
    matches: list[SimilarCaseMatchResult]
    total: int
