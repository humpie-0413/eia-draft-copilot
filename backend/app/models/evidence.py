import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Evidence(Base):
    """정규화된 증거 데이터.

    source_snapshot에서 추출·변환된 개별 데이터 포인트를 저장한다.
    screening_only=True인 행은 스크리닝 단계에서만 사용되며,
    본 평가 데이터와 분리하여 관리한다.
    """

    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 프로젝트 연결
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # 스냅샷 연결 (수동 입력 시 null 가능)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 데이터 소스 연결 (수동 입력 시 null 가능)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 환경 분야 (대기질, 수질, 소음·진동, 생태, 토양, 폐기물 등)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # 세부 지표명 (예: "PM10_연평균", "BOD", "소음_Leq_주간")
    indicator: Mapped[str] = mapped_column(String(200), nullable=False)

    # 측정값 (문자열로 저장 — 범위, 등급 등 비수치 값 대응)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    # 수치형 값 (집계·비교 용도, 파싱 가능할 때만 저장)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 단위 (예: "ug/m3", "mg/L", "dB(A)")
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 관측 시점
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 관측 위치 (PostGIS Point, EPSG:4326)
    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    # 추가 메타데이터 (측정소명, 출처 문서번호 등)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 스크리닝 전용 데이터 여부
    # True: 스크리닝(약식 평가) 단계에서만 사용, 본 평가 초안에 포함하지 않음
    # False: 본 평가용 데이터
    screening_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 관계
    project = relationship("Project", lazy="joined")
    snapshot = relationship("SourceSnapshot", back_populates="evidences", lazy="joined")
    data_source = relationship("DataSource", lazy="joined")
