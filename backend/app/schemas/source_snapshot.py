import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SnapshotStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class SourceSnapshotCreate(BaseModel):
    """소스 스냅샷 생성 요청."""

    data_source_id: uuid.UUID = Field(..., description="데이터 소스 ID")
    project_id: uuid.UUID = Field(..., description="프로젝트 ID")
    query_params: dict[str, Any] | None = Field(None, description="요청 파라미터")
    raw_payload: dict[str, Any] = Field(..., description="원시 응답 데이터")
    status: SnapshotStatus = Field(SnapshotStatus.SUCCESS, description="수집 상태")
    error_message: str | None = Field(None, description="오류 메시지")
    fetched_at: datetime | None = Field(None, description="API 호출 시각")


class SourceSnapshotRead(BaseModel):
    """소스 스냅샷 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    data_source_id: uuid.UUID
    project_id: uuid.UUID
    query_params: dict[str, Any] | None
    raw_payload: dict[str, Any]
    status: str
    error_message: str | None
    fetched_at: datetime
    created_at: datetime


class SourceSnapshotList(BaseModel):
    items: list[SourceSnapshotRead]
    total: int
