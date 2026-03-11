"""유사사례 모델.

과거 환경영향평가 사례를 저장하여 신규 프로젝트와의
유사도 비교 기반으로 참고 사례를 제공한다.
"""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SimilarCase(Base):
    """유사사례 — 과거 환경영향평가 참고 사례."""

    __tablename__ = "similar_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 사례 기본 정보
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 사업 유형 (Project.project_type과 동일 체계)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # 사업 위치 (PostGIS, EPSG:4326 — 대표 지점 또는 사업 경계)
    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True
    )

    # 사업 규모 (면적, 단위: m²)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 평가 완료 시점
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 평가서 요약
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 주요 발견사항 (환경 분야별 핵심 결론)
    key_findings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 해당 사례에서 다룬 환경 분야 목록 (예: ["air_quality", "water_quality"])
    evidence_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 원본 문서 URL
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 추가 메타데이터
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
