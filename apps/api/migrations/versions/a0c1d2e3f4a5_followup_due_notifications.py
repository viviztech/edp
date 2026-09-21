"""Support CRM follow-up due notification intents."""

import sqlalchemy as sa
from alembic import op

revision = "a0c1d2e3f4a5"
down_revision = "f9b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_intents", sa.Column("source_activity_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_notification_intent_activity",
        "notification_intents",
        "crm_lead_activities",
        ["source_activity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_notification_activity_recipient",
        "notification_intents",
        ["source_activity_id", "recipient_user_id"],
    )
    op.drop_constraint("notification_intent_topic", "notification_intents", type_="check")
    op.create_check_constraint(
        "notification_intent_topic",
        "notification_intents",
        "topic IN ('lead_assignment','followup_due')",
    )
    op.create_check_constraint(
        "notification_intent_source",
        "notification_intents",
        "(topic = 'lead_assignment' AND source_activity_id IS NULL) OR "
        "(topic = 'followup_due' AND source_activity_id IS NOT NULL)",
    )
    op.drop_constraint("notification_preference_topic", "notification_preferences", type_="check")
    op.create_check_constraint(
        "notification_preference_topic",
        "notification_preferences",
        "topic IN ('lead_assignment','followup_due')",
    )
    op.create_index("ix_crm_activity_due", "crm_lead_activities", ["due_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_crm_activity_due", table_name="crm_lead_activities")
    op.execute("DELETE FROM notification_intents WHERE topic = 'followup_due'")
    op.execute("DELETE FROM notification_preferences WHERE topic = 'followup_due'")
    op.drop_constraint("notification_preference_topic", "notification_preferences", type_="check")
    op.create_check_constraint(
        "notification_preference_topic", "notification_preferences", "topic IN ('lead_assignment')"
    )
    op.drop_constraint("notification_intent_source", "notification_intents", type_="check")
    op.drop_constraint("notification_intent_topic", "notification_intents", type_="check")
    op.create_check_constraint(
        "notification_intent_topic", "notification_intents", "topic IN ('lead_assignment')"
    )
    op.drop_constraint("uq_notification_activity_recipient", "notification_intents", type_="unique")
    op.drop_constraint(
        "fk_notification_intent_activity", "notification_intents", type_="foreignkey"
    )
    op.drop_column("notification_intents", "source_activity_id")
