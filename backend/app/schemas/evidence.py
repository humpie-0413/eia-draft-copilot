import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from geojson_pydantic import Point
from pydantic import BaseModel, ConfigDict, Field


class EvidenceCategory(str, Enum):
    """환경영향평가 증거 분야."""

    AIR_QUALITY = "air_quality"           # 대기질
    WATER_QUALITY = "water_quality"       # 수질
    NOISE_VIBRATION = "noise_vibration"   # 소음·진동
    ECOLOGY = "ecology"                   # 생태
    SOIL = "soil"                         # 토양
    WASTE = "waste"                       # 폐기물
    LANDSCAPE = "landscape"               # 경관
    CULTURAL_HERITAGE = "cultural_heritage"  # 문화재
    CLIMATE = "climate"                   # 기후
    LAND_USE = "land_use"                 # 토지이용
    TRAFFIC = "traffic"                   # 교통
    OTHER = "other"                       # 기타


class EvidenceCreate(BaseModel):
    """증거 데이터 생성 요청."""

    project_id: uuid.UUID = Field(..., description="프로젝트 ID")
    snapshot_id: uuid.UUID | None = Field(None, description="스냅샷 ID (자동 수집 시)")
    data_source_id: uuid.UUID | None = Field(None, description="데이터 소스 ID")
    category: EvidenceCategory = Field(..., description="환경 분야")
    indicator: str = Field(..., min_length=1, max_length=200, description="지표명")
    value: str = Field(..., min_length=1, max_length=255, description="측정값")
    numeric_value: float | None = Field(None, description="수치형 값")
    unit: str | None = Field(None, max_length=50, description="단위")
    observed_at: datetime | None = Field(None, description="관측 시점")
    location: Point | None = Field(None, description="관측 위치 (GeoJSON Point)")
    metadata_json: dict[str, Any] | None = Field(None, description="추가 메타데이터")
    screening_only: bool = Field(False, description="스크리닝 전용 데이터 여부")


class EvidenceUpdate(BaseModel):
    """증거 데이터 수정 요청."""

    category: EvidenceCategory | None = None
    indicator: str | None = Field(None, min_length=1, max_length=200)
    value: str | None = Field(None, min_length=1, max_length=255)
    numeric_value: float | None = None
    unit: str | None = None
    observed_at: datetime | None = None
    location: Point | None = None
    metadata_json: dict[str, Any] | None = None
    screening_only: bool | None = None


class EvidenceRead(BaseModel):
    """증거 데이터 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    data_source_id: uuid.UUID | None
    category: str
    indicator: str
    value: str
    numeric_value: float | None
    unit: str | None
    observed_at: datetime | None
    location: Point | None = None
    metadata_json: dict[str, Any] | None
    screening_only: bool
    created_at: datetime


class EvidenceList(BaseModel):
    items: list[EvidenceRead]
    total: int


class EvidenceFilter(BaseModel):
    """증거 조회 필터.

    screening_only 필드로 스크리닝 데이터와 본 평가 데이터를 분리 조회한다.
    """

    category: EvidenceCategory | None = None
    screening_only: bool | None = None
    data_source_id: uuid.UUID | None = None
