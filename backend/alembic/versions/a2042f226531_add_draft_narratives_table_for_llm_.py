"""add draft_narratives table for LLM enhanced text

Revision ID: a2042f226531
Revises: 003
Create Date: 2026-03-13 10:07:48.419141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a2042f226531'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('draft_narratives',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('section_key', sa.String(length=100), nullable=False),
        sa.Column('narrative_text', sa.Text(), nullable=False),
        sa.Column('adapter_used', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'section_key', name='uq_draft_narrative_project_section')
    )
    op.create_index(op.f('ix_draft_narratives_project_id'), 'draft_narratives', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_draft_narratives_project_id'), table_name='draft_narratives')
    op.drop_table('draft_narratives')
