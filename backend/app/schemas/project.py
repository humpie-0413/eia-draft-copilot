import uuid
from datetime import datetime
from enum import Enum

from geojson_pydantic import Feature, GeometryCollection, MultiPolygon, Point, Polygon
from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectType(str, Enum):
    ROAD = "road"               # 도로
    RAILWAY = "railway"         # 철도
    POWER_PLANT = "power_plant" # 발전소
    INDUSTRIAL = "industrial"   # 산업단지
    HOUSING = "housing"         # 주택단지
    AIRPORT = "airport"         # 공항
    PORT = "port"               # 항만
    DAM = "dam"                 # 댐
    RECLAMATION = "reclamation" # 매립
    OTHER = "other"             # 기타


# 허용하는 GeoJSON 지오메트리 타입
GeoJsonGeometry = Point | Polygon | MultiPolygon | GeometryCollection


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="프로젝트 이름")
    description: str | None = Field(None, description="프로젝트 설명")
    project_type: ProjectType | None = Field(None, description="사업 유형")
    geometry: GeoJsonGeometry | None = Field(None, description="사업 대상지 GeoJSON 지오메트리")


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    project_type: ProjectType | None = None
    status: ProjectStatus | None = None
    geometry: GeoJsonGeometry | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    project_type: str | None
    status: str
    geometry: GeoJsonGeometry | None = None
    created_at: datetime
    updated_at: datetime


class ProjectList(BaseModel):
    items: list[ProjectRead]
    total: int
