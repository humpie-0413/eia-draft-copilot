"""커넥터 수집 실행 관련 Pydantic 스키마."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    """커넥터 수집 요청."""

    project_id: uuid.UUID = Field(..., description="대상 프로젝트 ID")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="API 요청 파라미터 (측정소명, 기간 등)",
    )
    screening_only: bool = Field(
        False, description="스크리닝 전용 데이터 여부"
    )


class CollectResult(BaseModel):
    """커넥터 수집 결과."""

    connector_key: str = Field(..., description="커넥터 키")
    snapshot_id: uuid.UUID = Field(..., description="생성된 스냅샷 ID")
    status: str = Field(..., description="수집 상태 (success/error)")
    evidence_count: int = Field(..., description="생성된 증거 건수")
    error_message: str | None = Field(None, description="오류 메시지")
