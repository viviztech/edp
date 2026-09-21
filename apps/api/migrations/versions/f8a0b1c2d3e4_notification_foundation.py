"""Durable in-app notification intents and recipient preferences."""

import sqlalchemy as sa
from alembic import op

revision = "f8a0b1c2d3e4"
down_revision = "e7f8091a2b3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("topic", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", "topic"),
        sa.CheckConstraint("topic IN ('lead_assignment')", name="notification_preference_topic"),
        sa.CheckConstraint("version > 0", name="notification_preference_version"),
    )
    op.create_index(
        "ix_notification_preferences_organization_id",
        "notification_preferences",
        ["organization_id"],
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_table(
        "notification_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "recipient_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(40), nullable=False),
        sa.Column(
            "resource_id",
            sa.Uuid(),
            sa.ForeignKey("crm_leads.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "recipient_user_id", "event_key"),
        sa.CheckConstraint("topic IN ('lead_assignment')", name="notification_intent_topic"),
        sa.CheckConstraint(
            "state IN ('pending','delivered','suppressed')", name="notification_intent_state"
        ),
        sa.CheckConstraint("version > 0", name="notification_intent_version"),
    )
    op.create_index(
        "ix_notification_intents_organization_id", "notification_intents", ["organization_id"]
    )
    op.create_index(
        "ix_notification_intents_recipient_user_id", "notification_intents", ["recipient_user_id"]
    )
    op.create_index("ix_notification_dispatch", "notification_intents", ["state", "created_at"])
    op.create_index(
        "ix_notification_inbox",
        "notification_intents",
        ["organization_id", "recipient_user_id", "state", "id"],
    )


def downgrade() -> None:
    op.drop_table("notification_intents")
    op.drop_table("notification_preferences")
