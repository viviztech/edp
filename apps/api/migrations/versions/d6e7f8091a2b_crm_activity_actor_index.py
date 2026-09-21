"""Reconcile CRM activity indexes with model metadata."""

from alembic import op

revision = "d6e7f8091a2b"
down_revision = "c5d6e7f8091a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_crm_lead_activities_actor_user_id",
        "crm_lead_activities",
        ["actor_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crm_lead_activities_actor_user_id",
        table_name="crm_lead_activities",
    )
