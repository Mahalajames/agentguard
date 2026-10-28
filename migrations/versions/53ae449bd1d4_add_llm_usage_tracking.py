"""Add LLM usage tracking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "53ae449bd1d4"
down_revision: Union[str, Sequence[str], None] = "00c2453da078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the LLM usage tracking table."""
    op.create_table(
        "llm_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_llm_usage_created_at",
        "llm_usage",
        ["created_at"],
    )


def downgrade() -> None:
    """Remove the LLM usage tracking table."""
    op.drop_index("ix_llm_usage_created_at", table_name="llm_usage")
    op.drop_table("llm_usage")
