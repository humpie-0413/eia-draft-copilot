"""LLM 보강 서술문 저장 모델.

프로젝트+섹션별 LLM 보강 서술문을 저장하여
export 시 보강된 텍스트를 사용할 수 있도록 한다.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DraftNarrative(Base):
    __tablename__ = "draft_narratives"
    __table_args__ = (
        UniqueConstraint("project_id", "section_key", name="uq_draft_narrative_project_section"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_used: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
