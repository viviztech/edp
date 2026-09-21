"""Persist last CRM follow-up reminder recipient across notification purges."""

import sqlalchemy as sa
from alembic import op

revision = "a1d2e3f4a5b6"
down_revision = "a0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_lead_activities",
        sa.Column("reminder_queued_for_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_crm_activity_reminded_user",
        "crm_lead_activities",
        "users",
        ["reminder_queued_for_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_crm_activity_reminded_user", "crm_lead_activities", type_="foreignkey")
    op.drop_column("crm_lead_activities", "reminder_queued_for_user_id")
