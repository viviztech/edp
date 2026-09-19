"""crm export jobs"""

import sqlalchemy as sa
from alembic import op

revision = "92a3b4c5d6e7"
down_revision = "8192a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_export_jobs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("csv_content", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','failed')",
            name="crm_export_status",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND csv_content IS NOT NULL) OR "
            "(status <> 'completed' AND csv_content IS NULL)",
            name="crm_export_content_state",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_export_owner",
        "crm_export_jobs",
        ["organization_id", "requested_by_id", "created_at"],
    )
    op.create_index("ix_crm_export_jobs_expires_at", "crm_export_jobs", ["expires_at"])
    op.create_index(
        "ix_crm_export_jobs_organization_id",
        "crm_export_jobs",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_export_jobs_requested_by_id",
        "crm_export_jobs",
        ["requested_by_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_export_jobs_requested_by_id", table_name="crm_export_jobs")
    op.drop_index("ix_crm_export_jobs_expires_at", table_name="crm_export_jobs")
    op.drop_index("ix_crm_export_jobs_organization_id", table_name="crm_export_jobs")
    op.drop_index("ix_crm_export_owner", table_name="crm_export_jobs")
    op.drop_table("crm_export_jobs")
