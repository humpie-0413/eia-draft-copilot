import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DataSource(Base):
    """공공데이터 소스 레지스트리.

    각 행은 하나의 외부 데이터 소스(API)를 나타낸다.
    connector_key를 통해 해당 소스의 커넥터 구현체와 매핑된다.
    """

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # 소스 이름 (예: "한국환경공단 대기질", "물환경정보시스템")
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # 커넥터 식별 키 (예: "keco_air", "water_info")
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # API 기본 URL
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 소스 활성화 여부
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 관계
    snapshots = relationship("SourceSnapshot", back_populates="data_source", lazy="selectin")
