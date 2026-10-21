"""Align failure scenarios with CSV.

Revision ID: 00c2453da078
Revises: 1e14dd43f308
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "00c2453da078"
down_revision: Union[str, Sequence[str], None] = "1e14dd43f308"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the failure scenarios table with the CSV-aligned schema."""
    op.drop_table("failure_scenarios")

    op.create_table(
        "failure_scenarios",
        sa.Column("incident_id", sa.String(length=50), primary_key=True),
        sa.Column("incident_name", sa.String(length=500), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("incident_summary", sa.Text(), nullable=False),
        sa.Column("agent_type", sa.String(length=255), nullable=False),
        sa.Column("risk_dimension", sa.String(length=255), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("consequence", sa.Text(), nullable=False),
        sa.Column("lesson", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    """Restore the original failure scenarios table."""
    op.drop_table("failure_scenarios")

    op.create_table(
        "failure_scenarios",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("likelihood", sa.Integer(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
