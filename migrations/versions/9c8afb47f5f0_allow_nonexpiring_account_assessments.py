"""allow nonexpiring account assessments

Revision ID: 9c8afb47f5f0
Revises: 25e78c69e477
Create Date: 2026-11-14 12:08:56.057288

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c8afb47f5f0"
down_revision: Union[str, Sequence[str], None] = "25e78c69e477"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow account-owned assessments to have no expiration."""
    op.alter_column(
        "assessments",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    """Restore required assessment expiration."""
    op.execute(
        "UPDATE assessments "
        "SET expires_at = created_at + INTERVAL '24 hours' "
        "WHERE expires_at IS NULL"
    )
    op.alter_column(
        "assessments",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
