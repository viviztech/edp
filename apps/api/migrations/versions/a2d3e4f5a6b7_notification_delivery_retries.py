"""Track bounded notification dispatch failures."""

import sqlalchemy as sa
from alembic import op

revision = "a2d3e4f5a6b7"
down_revision = "a1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_intents",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "notification_intents",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_intents", sa.Column("error_code", sa.String(length=40), nullable=True)
    )
    op.drop_constraint("notification_intent_state", "notification_intents", type_="check")
    op.create_check_constraint(
        "notification_intent_state",
        "notification_intents",
        "state IN ('pending','retrying','failed','delivered','suppressed')",
    )
    op.create_check_constraint(
        "notification_intent_attempts",
        "notification_intents",
        "attempt_count >= 0 AND attempt_count <= 3",
    )
    op.create_index(
        "ix_notification_failures", "notification_intents", ["organization_id", "state", "id"]
    )


def downgrade() -> None:
    op.execute(
        "UPDATE notification_intents SET state = 'pending' WHERE state IN ('retrying','failed')"
    )
    op.drop_index("ix_notification_failures", table_name="notification_intents")
    op.drop_constraint("notification_intent_attempts", "notification_intents", type_="check")
    op.drop_constraint("notification_intent_state", "notification_intents", type_="check")
    op.create_check_constraint(
        "notification_intent_state",
        "notification_intents",
        "state IN ('pending','delivered','suppressed')",
    )
    op.drop_column("notification_intents", "error_code")
    op.drop_column("notification_intents", "next_attempt_at")
    op.drop_column("notification_intents", "attempt_count")
