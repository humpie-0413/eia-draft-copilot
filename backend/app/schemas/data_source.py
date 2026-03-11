import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DataSourceCreate(BaseModel):
    """공공데이터 소스 등록 요청."""

    name: str = Field(..., min_length=1, max_length=255, description="소스 이름")
    connector_key: str = Field(..., min_length=1, max_length=100, description="커넥터 식별 키")
    base_url: str | None = Field(None, max_length=500, description="API 기본 URL")
    description: str | None = Field(None, description="소스 설명")
    enabled: bool = Field(True, description="활성화 여부")


class DataSourceUpdate(BaseModel):
    """공공데이터 소스 수정 요청."""

    name: str | None = Field(None, min_length=1, max_length=255)
    connector_key: str | None = Field(None, min_length=1, max_length=100)
    base_url: str | None = None
    description: str | None = None
    enabled: bool | None = None


class DataSourceRead(BaseModel):
    """공공데이터 소스 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    connector_key: str
    base_url: str | None
    description: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class DataSourceList(BaseModel):
    items: list[DataSourceRead]
    total: int
