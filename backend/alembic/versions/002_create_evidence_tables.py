"""data_sources, source_snapshots, evidences 테이블 생성

Revision ID: 002
Revises: 001
Create Date: 2026-03-12

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- data_sources ---
    op.create_table(
        "data_sources",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("connector_key", sa.String(100), nullable=False, unique=True),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
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

    # --- source_snapshots ---
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "data_source_id",
            sa.UUID(),
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_params", JSONB, nullable=True),
        sa.Column("raw_payload", JSONB, nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="success",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    # 프로젝트별 스냅샷 조회 인덱스
    op.create_index(
        "idx_snapshots_project_id",
        "source_snapshots",
        ["project_id"],
    )
    op.create_index(
        "idx_snapshots_data_source_id",
        "source_snapshots",
        ["data_source_id"],
    )

    # --- evidences ---
    op.create_table(
        "evidences",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.UUID(),
            sa.ForeignKey("source_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "data_source_id",
            sa.UUID(),
            sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("indicator", sa.String(200), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("screening_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    # 프로젝트별 증거 조회 인덱스
    op.create_index(
        "idx_evidences_project_id",
        "evidences",
        ["project_id"],
    )
    # 스크리닝/본평가 분리 조회용 복합 인덱스
    op.create_index(
        "idx_evidences_project_screening",
        "evidences",
        ["project_id", "screening_only"],
    )
    # 분야별 조회 인덱스
    op.create_index(
        "idx_evidences_category",
        "evidences",
        ["category"],
    )
    # 공간 인덱스
    op.create_index(
        "idx_evidences_location",
        "evidences",
        ["location"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("idx_evidences_location", table_name="evidences")
    op.drop_index("idx_evidences_category", table_name="evidences")
    op.drop_index("idx_evidences_project_screening", table_name="evidences")
    op.drop_index("idx_evidences_project_id", table_name="evidences")
    op.drop_table("evidences")

    op.drop_index("idx_snapshots_data_source_id", table_name="source_snapshots")
    op.drop_index("idx_snapshots_project_id", table_name="source_snapshots")
    op.drop_table("source_snapshots")

    op.drop_table("data_sources")
