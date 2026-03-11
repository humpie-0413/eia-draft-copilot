import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SourceSnapshot(Base):
    """소스 스냅샷 — 외부 API에서 가져온 원시 데이터를 그대로 보존한다.

    raw_payload에 응답 전문을 JSONB로 저장하여,
    정규화 로직 변경 시 재처리할 수 있도록 한다.
    """

    __tablename__ = "source_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 어떤 데이터 소스에서 가져왔는지
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )

    # 어떤 프로젝트를 위해 수집했는지
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # 요청 시 사용한 파라미터 (재현 가능하도록 기록)
    query_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 원시 응답 전문
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # 수집 상태
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="success", server_default="success"
    )

    # 오류 발생 시 메시지
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 실제 API 호출 시각
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 관계
    data_source = relationship("DataSource", back_populates="snapshots", lazy="joined")
    project = relationship("Project", lazy="joined")
    evidences = relationship("Evidence", back_populates="snapshot", lazy="selectin")
