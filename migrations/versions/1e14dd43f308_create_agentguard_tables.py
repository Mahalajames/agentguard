"""Create AgentGuard tables."""

import sqlalchemy as sa
from alembic import op

revision = "1e14dd43f308"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all AgentGuard tables."""
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("token", sa.String(32), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
    )

    op.create_table(
        "agent_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(36),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("result_data", sa.JSON(), nullable=False),
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_result_id",
            sa.String(36),
            sa.ForeignKey("agent_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule", sa.String(100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )

    op.create_table(
        "safeguards",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("trigger_condition", sa.Text(), nullable=False),
        sa.Column("safeguard_text", sa.Text(), nullable=False),
        sa.Column("nist_ai_rmf_function", sa.String(20), nullable=False),
        sa.Column("nist_ai_rmf_subcategory", sa.String(100), nullable=False),
        sa.Column("owasp_reference", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("effort", sa.String(20), nullable=False),
    )

    op.create_table(
        "failure_scenarios",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("likelihood", sa.Integer(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    """Remove all AgentGuard tables."""
    op.drop_table("failure_scenarios")
    op.drop_table("safeguards")
    op.drop_table("findings")
    op.drop_table("agent_results")
    op.drop_table("agents")
    op.drop_table("assessments")
    op.drop_table("organizations")
