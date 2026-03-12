"""similar_cases 테이블 생성 — 유사사례 매칭 시스템

Revision ID: 003
Revises: 002
Create Date: 2026-03-12

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "similar_cases",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_type", sa.String(100), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="GEOMETRY", srid=4326),
            nullable=True,
        ),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_findings", JSONB, nullable=True),
        sa.Column("evidence_categories", JSONB, nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # 사업 유형별 조회 인덱스
    op.create_index(
        "idx_similar_cases_project_type",
        "similar_cases",
        ["project_type"],
    )

    # 공간 인덱스 — GeoAlchemy2가 자동 생성하므로 중복 방지
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'idx_similar_cases_location'
            ) THEN
                CREATE INDEX idx_similar_cases_location ON similar_cases USING gist (location);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("idx_similar_cases_location", table_name="similar_cases")
    op.drop_index("idx_similar_cases_project_type", table_name="similar_cases")
    op.drop_table("similar_cases")
